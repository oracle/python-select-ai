# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Public A2A/A2UI gateway for temporary Select AI database sessions."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import requests
from a2a.compat.v0_3.conversions import to_compat_agent_card
from a2a.helpers import (
    new_artifact,
    new_text_part,
)
from a2a.server.context import ServerCallContext
from a2a.server.owner_resolver import resolve_user_scope
from a2a.server.request_handlers import RequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from a2a.types.a2a_pb2 import (
    AgentCard as AgentCardMessage,
)
from a2a.types.a2a_pb2 import (
    CancelTaskRequest,
    GetExtendedAgentCardRequest,
    GetTaskRequest,
    ListTasksRequest,
    ListTasksResponse,
    Message,
    SendMessageRequest,
    Task,
    TaskState,
    TaskStatus,
)
from a2a.utils.errors import (
    InvalidParamsError,
    TaskNotFoundError,
    UnsupportedOperationError,
)
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from select_ai.agent.a2a.a2ui import (
    A2UI_EXTENSION_URI,
    A2UI_MIME_TYPE,
    a2ui_extension,
    a2ui_part,
    find_action,
)
from select_ai.agent.a2a.auth import (
    add_bearer_security,
    authentication_middleware,
)
from select_ai.agent.a2a.forms import (
    connection_form,
    validate_connection_form,
)
from select_ai.agent.a2a.models import ConnectionConfig, GatewaySettings
from select_ai.agent.a2a.worker_client import ReconnectRequired, WorkerClient
from select_ai.version import __version__

_CONNECTION_ACTION_NAME = "submit_database_connection"
_CONNECTION_SUCCESS_MESSAGE = "Connected. Ask a database question."
_CONNECTION_FAILURE_MESSAGE = (
    "Could not connect. Check the DSN, credentials, and team name."
)
_BOOTSTRAP_TASK_ID_PREFIX = "gateway-bootstrap-"


async def _unsupported_operation(*_args, **_kwargs):
    """Reject an A2A operation not advertised by the gateway."""
    raise UnsupportedOperationError


class _UnsupportedStream:
    """Async iterator that reports unsupported streaming when consumed."""

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise UnsupportedOperationError


def _unsupported_stream(*_args, **_kwargs):
    """Return an async iterator that rejects an unsupported A2A stream."""
    return _UnsupportedStream()


class GatewayRequestHandler(RequestHandler):
    """Proxy A2A requests to the Oracle-backed handler in a worker child."""

    def __init__(
        self,
        worker_client: WorkerClient,
        agent_card: AgentCard,
        connection: ConnectionConfig | None = None,
        connection_form_template: tuple[dict, ...] | None = None,
        allow_unauthenticated: bool = False,
    ):
        self.worker_client = worker_client
        self.agent_card = agent_card
        self.connection = connection or ConnectionConfig()
        self.connection_form_template = connection_form_template
        self.allow_unauthenticated = allow_unauthenticated

    # RequestHandler requires every operation even when the Agent Card does
    # not advertise streaming or push notifications.
    on_message_send_stream = _unsupported_stream
    on_create_task_push_notification_config = _unsupported_operation
    on_get_task_push_notification_config = _unsupported_operation
    on_list_task_push_notification_configs = _unsupported_operation
    on_delete_task_push_notification_config = _unsupported_operation
    on_subscribe_to_task = _unsupported_stream

    async def on_message_send(
        self,
        params: SendMessageRequest,
        context: ServerCallContext,
    ) -> Task | Message:
        """Handle connection bootstrap or forward the request to a worker."""
        message = params.message
        owner = self._owner(context)
        if action := find_action(message, _CONNECTION_ACTION_NAME):
            return await self._handle_connection_action(message, action, owner)

        response = await self._recover_task_context(message, owner)
        if response is not None:
            return response

        context_id = self._ensure_context_id(message)
        had_task_id = bool(message.task_id)

        if not await asyncio.to_thread(
            self.worker_client.session_exists,
            owner,
            context_id,
        ):
            if self._connection_config.missing_fields:
                return self._build_connection_form_task(
                    task_id=message.task_id or None,
                    context_id=context_id,
                    history=None if had_task_id else [message],
                )
            if await self._open_session({}, owner, context_id) is None:
                return self._build_connection_failure_task(
                    task_id=message.task_id or None,
                    context_id=context_id,
                    history=None if had_task_id else [message],
                )

        return await self._forward_message(owner, context_id, params)

    async def _handle_connection_action(
        self,
        message: Message,
        action: dict,
        owner: str,
    ) -> Task:
        """Open a database session from the submitted A2UI form."""
        if not message.context_id:
            raise InvalidParamsError(
                "A database connection action requires contextId."
            )

        task = _new_bootstrap_task(
            task_id=message.task_id or None,
            context_id=message.context_id,
        )
        session_id = await self._open_session(
            action.get("context") or {},
            owner,
            message.context_id,
        )
        if session_id is None:
            return self._build_connection_failure_task(
                task_id=task.id,
                context_id=task.context_id,
            )
        return self._complete_task(
            task,
            [new_text_part(_CONNECTION_SUCCESS_MESSAGE)],
            "database-session",
        )

    async def _recover_task_context(
        self,
        message: Message,
        owner: str,
    ) -> Task | None:
        """Recover a context when a client sends only a previous task ID."""
        if message.context_id or not message.task_id:
            return None

        try:
            existing_task = await asyncio.to_thread(
                self.worker_client.get_task,
                owner,
                GetTaskRequest(id=message.task_id),
            )
        except ReconnectRequired as error:
            if error.session_id is None:
                raise
            return self._build_connection_form_task(
                task_id=message.task_id or None,
                context_id=error.session_id,
            )
        if existing_task is None:
            # Gemini Enterprise may resume a conversation with only its
            # previous taskId. Task routing metadata is intentionally
            # ephemeral, so it can be absent after a deployment or Consul
            # restart even though the Gemini conversation still exists.
            return self._build_connection_form_task(
                task_id=message.task_id,
                context_id=str(uuid4()),
            )
        message.context_id = existing_task.context_id
        return None

    @staticmethod
    def _ensure_context_id(message: Message) -> str:
        """Assign a context ID to a new message when one was not provided."""
        if message.context_id:
            return message.context_id
        context_id = str(uuid4())
        message.context_id = context_id
        return context_id

    async def _forward_message(
        self,
        owner: str,
        context_id: str,
        params: SendMessageRequest,
    ) -> Task | Message:
        """Forward a message and turn worker loss into a reconnect task."""
        try:
            try:
                result = await asyncio.to_thread(
                    self.worker_client.send_message,
                    owner,
                    context_id,
                    params,
                )
            except TaskNotFoundError:
                # Gemini continues the gateway's transient connection-form
                # task after the database session opens. That task was never
                # persisted in Oracle, so let the worker create its first
                # durable task while retaining the connected context.
                if not params.message.task_id.startswith(
                    _BOOTSTRAP_TASK_ID_PREFIX
                ):
                    raise
                params.message.ClearField("task_id")
                result = await asyncio.to_thread(
                    self.worker_client.send_message,
                    owner,
                    context_id,
                    params,
                )
        except ReconnectRequired:
            return self._build_connection_form_task(
                task_id=params.message.task_id or None,
                context_id=context_id,
                history=(None if params.message.task_id else [params.message]),
            )
        if isinstance(result, (Task, Message)):
            return result
        raise RuntimeError("The worker returned no A2A response.")

    async def _open_session(
        self,
        action_context: dict,
        owner: str,
        context_id: str,
    ) -> str | None:
        try:
            session_info = self._connection_config.resolve(action_context)
            session_id = await asyncio.to_thread(
                self.worker_client.open_session,
                owner,
                context_id,
                session_info,
            )
            return session_id
        except (requests.RequestException, ValueError, RuntimeError):
            return None

    async def on_get_task(
        self,
        params: GetTaskRequest,
        context: ServerCallContext,
    ) -> Task | None:
        try:
            task = await asyncio.to_thread(
                self.worker_client.get_task,
                self._owner(context),
                params,
            )
        except ReconnectRequired as error:
            if error.session_id is None:
                raise
            return self._build_connection_form_task(
                task_id=params.id,
                context_id=error.session_id,
            )
        if task is None:
            return self._build_connection_form_task(
                task_id=params.id,
                context_id=str(uuid4()),
            )
        return task

    async def on_list_tasks(
        self,
        params: ListTasksRequest,
        context: ServerCallContext,
    ) -> ListTasksResponse:
        if not params.context_id:
            raise InvalidParamsError(
                "ListTasks requires contextId for this gateway."
            )
        try:
            return await asyncio.to_thread(
                self.worker_client.list_tasks,
                self._owner(context),
                params.context_id,
                params,
            )
        except ReconnectRequired as error:
            raise self._session_expired_error(params.context_id) from error

    async def on_cancel_task(
        self,
        params: CancelTaskRequest,
        context: ServerCallContext,
    ) -> Task | None:
        try:
            task = await asyncio.to_thread(
                self.worker_client.cancel_task,
                self._owner(context),
                params.id,
            )
        except ReconnectRequired as error:
            if error.session_id is None:
                raise
            return self._build_connection_form_task(
                task_id=params.id,
                context_id=error.session_id,
            )
        if task is None:
            return self._build_connection_form_task(
                task_id=params.id,
                context_id=str(uuid4()),
            )
        return task

    async def on_get_extended_agent_card(
        self,
        _params: GetExtendedAgentCardRequest,
        _context: ServerCallContext,
    ) -> AgentCardMessage:
        return self.agent_card

    def _session_expired_error(self, context_id: str) -> InvalidParamsError:
        """Build the reconnect error returned by the task-list operation."""
        return InvalidParamsError(
            "Database session expired. Reconnect using contextId.",
            data={
                "reason": "SESSION_EXPIRED",
                "contextId": context_id,
                "connectionForm": connection_form(
                    missing_fields=self._connection_config.missing_fields,
                    template=self._form_template,
                ),
            },
        )

    @staticmethod
    def _add_artifact(
        task: Task,
        parts: list,
        name: str,
        extensions: list[str] | None = None,
    ) -> None:
        artifact = new_artifact(parts, name)
        if extensions:
            artifact.extensions.extend(extensions)
        task.artifacts.add().CopyFrom(artifact)

    def _complete_task(
        self,
        task: Task,
        parts: list,
        name: str,
        extensions: list[str] | None = None,
    ) -> Task:
        self._add_artifact(task, parts, name, extensions)
        task.status.state = TaskState.TASK_STATE_COMPLETED
        task.status.timestamp.GetCurrentTime()
        return task

    def _build_connection_form_task(
        self,
        *,
        task_id: str | None,
        context_id: str,
        history: list[Message] | None = None,
    ) -> Task:
        """Build a completed, transient task containing the connection form."""
        if not self._connection_config.missing_fields:
            return self._build_connection_failure_task(
                task_id=task_id,
                context_id=context_id,
                history=history,
            )
        task = _new_bootstrap_task(
            task_id=task_id,
            context_id=context_id,
            history=history,
        )
        return self._complete_task(
            task,
            self._connection_form_parts(task.id),
            "database-connection-form",
            [A2UI_EXTENSION_URI],
        )

    def _build_connection_failure_task(
        self,
        *,
        task_id: str | None,
        context_id: str,
        history: list[Message] | None = None,
    ) -> Task:
        """Return a safe failure and a fresh form when input is still needed."""
        task = _new_bootstrap_task(
            task_id=task_id,
            context_id=context_id,
            history=history,
        )
        parts = [new_text_part(_CONNECTION_FAILURE_MESSAGE)]
        parts.extend(self._connection_form_parts(task.id))
        extensions = [A2UI_EXTENSION_URI] if len(parts) > 1 else None
        return self._complete_task(
            task,
            parts,
            "database-connection-failure",
            extensions,
        )

    def _connection_form_parts(self, task_id: str) -> list:
        return [
            a2ui_part(item)
            for item in connection_form(
                surface_id=f"db-connect-{task_id}",
                missing_fields=self._connection_config.missing_fields,
                template=self._form_template,
            )
        ]

    @property
    def _connection_config(self) -> ConnectionConfig:
        return getattr(self, "connection", ConnectionConfig())

    @property
    def _form_template(self) -> tuple[dict, ...] | None:
        return getattr(self, "connection_form_template", None)

    def _owner(self, context: ServerCallContext) -> str:
        """Resolve the SDK owner, allowing one explicit local-only scope."""
        owner = resolve_user_scope(context)
        if owner:
            return owner
        if getattr(self, "allow_unauthenticated", True):
            return "local-development"
        raise PermissionError("Bearer authentication is required.")


def _new_bootstrap_task(
    *,
    task_id: str | None,
    context_id: str,
    history: list[Message] | None = None,
) -> Task:
    """Build a transient response task for the connection bootstrap."""
    return Task(
        id=task_id or f"{_BOOTSTRAP_TASK_ID_PREFIX}{uuid4()}",
        context_id=context_id,
        status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
        history=history or [],
    )


def create_gateway_app(settings: GatewaySettings) -> Starlette:
    """Build a Gemini Enterprise-compatible A2A v0.3 gateway application."""
    form_template = settings.connection_form_template
    if form_template is not None:
        form_template = validate_connection_form(
            list(form_template),
            settings.connection.missing_fields,
        )
    return create_session_app(
        public_url=settings.public_url,
        session_client=WorkerClient(settings),
        connection=settings.connection,
        connection_form_template=form_template,
        allow_unauthenticated=settings.allow_unauthenticated,
        description=settings.description,
    )


def create_session_app(
    *,
    public_url: str,
    session_client,
    connection: ConnectionConfig,
    connection_form_template: tuple[dict, ...] | None,
    allow_unauthenticated: bool,
    description: str | None = None,
    lifespan=None,
) -> Starlette:
    """Build the common dynamic-session A2A application."""
    description = description or (
        "Connects a user to a temporary Select AI database session."
    )
    endpoint = f"{public_url.rstrip('/')}/a2a/jsonrpc/"
    card = AgentCard(
        name="Select AI Database Agent",
        description=description,
        version=__version__,
        default_input_modes=["text/plain", A2UI_MIME_TYPE],
        default_output_modes=["text/plain", A2UI_MIME_TYPE],
        capabilities=AgentCapabilities(
            streaming=False,
            extensions=[a2ui_extension()],
        ),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=endpoint,
            ),
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="0.3",
                url=endpoint,
            ),
        ],
        skills=[
            AgentSkill(
                id="database_connect",
                name="Connect to database",
                description=description,
                tags=["oracle", "select-ai"],
                examples=[],
                input_modes=["text/plain", A2UI_MIME_TYPE],
                output_modes=["text/plain", A2UI_MIME_TYPE],
            )
        ],
    )
    if not allow_unauthenticated:
        add_bearer_security(card)
    handler = GatewayRequestHandler(
        session_client,
        card,
        connection,
        connection_form_template,
        allow_unauthenticated,
    )
    compat_card = to_compat_agent_card(card).model_dump(
        by_alias=True,
        exclude_none=True,
    )

    async def get_agent_card(_request):
        return JSONResponse(compat_card)

    routes = [
        Route("/.well-known/agent-card.json", get_agent_card, methods=["GET"])
    ]
    routes.extend(
        create_jsonrpc_routes(
            handler,
            rpc_url="/a2a/jsonrpc/",
            enable_v0_3_compat=True,
        )
    )
    return Starlette(
        routes=routes,
        middleware=authentication_middleware(allow_unauthenticated),
        lifespan=lifespan,
    )
