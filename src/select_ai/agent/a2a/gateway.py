# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Public A2A/A2UI gateway for temporary Select AI database sessions."""

from __future__ import annotations

import asyncio

from a2a.compat.v0_3.conversions import to_compat_agent_card
from a2a.helpers import (
    new_data_part,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from google.protobuf.json_format import MessageToDict, ParseDict
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from select_ai.agent.a2a.a2ui import (
    A2UI_EXTENSION_URI,
    A2UI_MIME_TYPE,
    a2ui_extension,
)
from select_ai.agent.a2a.forms import connection_form
from select_ai.agent.a2a.models import GatewaySettings, SessionInfo
from select_ai.agent.a2a.results import add_team_result
from select_ai.agent.a2a.worker_client import ReconnectRequired, WorkerClient
from select_ai.version import __version__


class GatewayExecutor(AgentExecutor):
    """Route each A2A context to one in-memory worker session."""

    def __init__(self, worker_client: WorkerClient):
        self.worker_client = worker_client
        self.sessions: dict[str, str] = {}

    async def execute(self, context, event_queue):
        task = context.current_task or new_task_from_user_message(
            context.message
        )
        if context.current_task is None:
            await event_queue.enqueue_event(task)
        context_id = task.context_id or task.id
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.start_work()
        action = self._a2ui_action(context)
        if action and action.get("name") == "submit_database_connection":
            parts = await self._open_session(
                action.get("context", {}),
                context_id,
            )
            artifact_name = "database-session"
            extensions = None
        elif context_id not in self.sessions:
            parts = [_a2ui_part(message) for message in connection_form()]
            artifact_name = "database-connection-form"
            extensions = [A2UI_EXTENSION_URI]
        else:
            result = await self._send_prompt(
                context_id,
                context.get_user_input(),
            )
            await add_team_result(updater, result)
            await updater.complete()
            return
        await updater.add_artifact(
            parts=parts,
            name=artifact_name,
            last_chunk=True,
            extensions=extensions,
        )
        await updater.complete()

    async def _open_session(self, action_context: dict, context_id: str):
        try:
            session_info = SessionInfo.from_a2ui_event(action_context)
            session_id = await asyncio.to_thread(
                self.worker_client.open_session,
                context_id,
                session_info,
            )
        except (ValueError, RuntimeError):
            return [
                new_text_part(
                    "Could not connect. Check the DSN, credentials, and team "
                    "name."
                )
            ]
        self.sessions[context_id] = session_id
        return [new_text_part("Connected. Ask a database question.")]

    async def _send_prompt(self, context_id: str, prompt: str) -> str | None:
        try:
            result = await asyncio.to_thread(
                self.worker_client.send_prompt,
                self.sessions[context_id],
                prompt,
            )
        except ReconnectRequired:
            self.sessions.pop(context_id, None)
            return "Your database session ended. Please reconnect."
        return result

    async def cancel(self, context, event_queue):
        """Close the live worker session when the A2A task is cancelled."""
        task = context.current_task
        if task is None:
            return
        context_id = task.context_id or task.id
        session_id = self.sessions.pop(context_id, None)
        if session_id:
            await asyncio.to_thread(
                self.worker_client.close_session,
                session_id,
            )
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.cancel()

    @staticmethod
    def _a2ui_action(context) -> dict | None:
        for part in context.message.parts:
            if part.WhichOneof("content") != "data":
                continue
            data = MessageToDict(part.data)
            messages = data if isinstance(data, list) else [data]
            for message in messages:
                if (
                    not isinstance(message, dict)
                    or message.get("version") != "v0.9"
                ):
                    continue
                action = message.get("action")
                if isinstance(action, dict):
                    return action
        return None


def _a2ui_part(message: dict):
    """Encode one A2UI operation in the format used by Gemini Enterprise."""
    part = new_data_part(message)
    ParseDict({"mimeType": A2UI_MIME_TYPE}, part.metadata)
    return part


def create_gateway_app(settings: GatewaySettings) -> Starlette:
    """Build a Gemini Enterprise-compatible A2A v0.3 gateway application."""
    description = "Connects a user to a temporary Select AI database session."
    endpoint = f"{settings.agent_url}/a2a/jsonrpc/"
    card = AgentCard(
        name="Select AI Database Gateway",
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
    handler = DefaultRequestHandler(
        agent_executor=GatewayExecutor(WorkerClient(settings)),
        task_store=InMemoryTaskStore(),
        agent_card=card,
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
    return Starlette(routes=routes)
