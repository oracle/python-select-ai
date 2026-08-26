# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A2A HTTP server for Oracle Database AI Agent Teams."""

from contextlib import asynccontextmanager
from typing import Optional

from a2a.compat.v0_3.conversions import to_compat_agent_card
from a2a.helpers import new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import select_ai
from select_ai.agent import AsyncTeam
from select_ai.agent.a2a.context_store import OracleContextStore
from select_ai.agent.a2a.task_store import OracleTaskStore
from select_ai.version import __version__


class DatabaseTeamExecutor(AgentExecutor):
    """Execute A2A requests with one Oracle conversation per A2A context."""

    def __init__(self, team_name: str, context_store: OracleContextStore):
        self.team_name = team_name
        self.context_store = context_store

    async def execute(self, context, event_queue):
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.start_work()
        conversation_id = await self.context_store.get_or_create(
            context_id=task.context_id or task.id,
            context=context.call_context,
            team_name=self.team_name,
        )
        result = await AsyncTeam(team_name=self.team_name).run(
            prompt=context.get_user_input(),
            params={"conversation_id": conversation_id},
        )
        await updater.add_artifact(
            parts=[new_text_part(result or "")],
            name="database-agent-result",
            last_chunk=True,
        )
        await updater.complete()

    async def cancel(self, context, event_queue):
        if context.current_task is None:
            return
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.current_task.id,
            context_id=context.current_task.context_id,
        )
        await updater.cancel()


def create_app(  # noqa: PLR0913
    team_name: str,
    public_url: str,
    user: str,
    password: str,
    dsn: str,
    wallet_location: Optional[str] = None,
    wallet_password: Optional[str] = None,
    description: Optional[str] = None,
    pool_max_size: int = 10,
) -> Starlette:
    """Build an A2A JSON-RPC application for one database AI Agent Team."""
    if pool_max_size < 1:
        raise ValueError("pool_max_size must be at least 1")

    agent_card = _build_agent_card(team_name, public_url, description)
    compat_agent_card = _build_v03_agent_card(agent_card)
    task_store = OracleTaskStore()
    context_store = OracleContextStore()
    handler = DefaultRequestHandler(
        agent_executor=DatabaseTeamExecutor(team_name, context_store),
        task_store=task_store,
        agent_card=agent_card,
    )

    @asynccontextmanager
    async def lifespan(app):
        connect_args = {
            "user": user,
            "password": password,
            "dsn": dsn,
            "min_size": 1,
            "max_size": pool_max_size,
        }
        if wallet_location:
            connect_args["wallet_location"] = wallet_location
            connect_args["config_dir"] = wallet_location
        if wallet_password:
            connect_args["wallet_password"] = wallet_password
        select_ai.create_pool_async(**connect_args)
        try:
            await task_store.initialize()
            await context_store.initialize()
            yield
        finally:
            await select_ai.async_disconnect()

    async def get_agent_card(request):
        """Serve the documented A2A v0.3 card required by Gemini Enterprise."""
        return JSONResponse(compat_agent_card)

    routes = [
        Route(
            "/.well-known/agent-card.json",
            get_agent_card,
            methods=["GET"],
        )
    ]
    routes.extend(
        create_jsonrpc_routes(
            handler,
            rpc_url="/a2a/jsonrpc/",
            enable_v0_3_compat=True,
        )
    )
    return Starlette(routes=routes, lifespan=lifespan)


def _build_agent_card(
    team_name: str,
    public_url: str,
    description: Optional[str],
) -> AgentCard:
    description = description or f"Oracle Database AI agent team {team_name}."
    endpoint = f"{public_url.rstrip('/')}/a2a/jsonrpc/"
    return AgentCard(
        name=team_name,
        description=description,
        version=__version__,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
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
                id=team_name.lower(),
                name=team_name,
                description=description,
                tags=["oracle", "database", "select-ai"],
                examples=[],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            )
        ],
    )


def _build_v03_agent_card(agent_card: AgentCard) -> dict:
    """Return the standalone A2A v0.3 discovery representation."""
    return to_compat_agent_card(agent_card).model_dump(
        by_alias=True, exclude_none=True
    )
