# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A database-bound A2A runtime for one temporary worker session."""

from __future__ import annotations

from a2a.auth.user import User
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types.a2a_pb2 import (
    CancelTaskRequest,
    GetTaskRequest,
    ListTasksRequest,
    SendMessageRequest,
)
from a2a.utils.errors import TaskNotFoundError

from select_ai.agent import AsyncTeam
from select_ai.agent.a2a.context_store import OracleContextStore
from select_ai.agent.a2a.server import DatabaseTeamExecutor, _build_agent_card
from select_ai.agent.a2a.task_store import OracleTaskStore
from select_ai.agent.a2a.worker_protocol import (
    A2AMethod,
    ResultKind,
    WorkerResult,
    encode_result,
    parse_request,
)

_METHOD_HANDLERS = {
    A2AMethod.SEND_MESSAGE: (SendMessageRequest, "on_message_send"),
    A2AMethod.GET_TASK: (GetTaskRequest, "on_get_task"),
    A2AMethod.LIST_TASKS: (ListTasksRequest, "on_list_tasks"),
    A2AMethod.CANCEL_TASK: (CancelTaskRequest, "on_cancel_task"),
}


class SessionUser(User):
    """Internal A2A user used to scope one worker session's database rows."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def user_name(self) -> str:
        return self.session_id


class SessionRuntime:
    """Own the A2A handler and Oracle stores for one connected database."""

    def __init__(self, session_id: str, team_name: str) -> None:
        self.session_id = session_id
        self.team_name = team_name
        self.task_store = OracleTaskStore()
        self.context_store = OracleContextStore()
        self.handler: DefaultRequestHandler | None = None

    async def initialize(self) -> None:
        """Initialize Oracle-backed stores after the worker connects."""
        # Validate the user-supplied team before the worker reports this
        # database session as ready.  Without this check, invalid team names
        # appear to connect successfully and fail only on the first prompt.
        await AsyncTeam.fetch(self.team_name)
        await self.task_store.initialize()
        await self.context_store.initialize()
        self.handler = DefaultRequestHandler(
            agent_executor=DatabaseTeamExecutor(
                self.team_name,
                self.context_store,
            ),
            task_store=self.task_store,
            agent_card=_build_agent_card(
                self.team_name,
                f"http://worker/sessions/{self.session_id}",
                None,
            ),
        )

    async def handle(
        self,
        method: A2AMethod | str,
        payload: bytes,
    ) -> WorkerResult:
        """Handle one internal A2A operation using protobuf wire bytes."""
        if self.handler is None:
            raise RuntimeError("A2A session runtime is not initialized.")

        operation = A2AMethod(method)
        context = ServerCallContext(user=SessionUser(self.session_id))
        if operation == A2AMethod.DELETE_TASK:
            request = parse_request(GetTaskRequest, payload)
            await self.task_store.delete(request.id, context)
            return encode_result(None)

        try:
            request_type, handler_name = _METHOD_HANDLERS[operation]
        except KeyError as error:
            raise ValueError(
                f"Unsupported worker A2A method: {operation.value}"
            ) from error

        request = parse_request(request_type, payload)
        try:
            result = await getattr(self.handler, handler_name)(
                request,
                context,
            )
        except TaskNotFoundError:
            return WorkerResult(ResultKind.TASK_NOT_FOUND)
        return encode_result(result)
