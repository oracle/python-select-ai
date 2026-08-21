# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A2A HTTP server support for Oracle Database AI agent teams."""

from asyncio import Lock
from contextlib import asynccontextmanager
from typing import Optional

import select_ai
from select_ai.agent import AsyncTeam
from select_ai.version import __version__


def _a2a_imports():
    """Load optional A2A dependencies only when the server is requested."""
    try:
        from a2a.helpers import new_task_from_user_message, new_text_part
        from a2a.server.agent_execution import AgentExecutor
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.routes import (
            create_agent_card_routes,
            create_jsonrpc_routes,
        )
        from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
        from a2a.types import (
            AgentCapabilities,
            AgentCard,
            AgentInterface,
            AgentSkill,
        )
        from starlette.applications import Starlette
    except ImportError as exc:
        raise RuntimeError(
            "A2A server support requires the optional 'a2a' extra. "
            "Install it with: pip install 'select_ai[a2a]'"
        ) from exc

    return {
        "AgentCapabilities": AgentCapabilities,
        "AgentCard": AgentCard,
        "AgentExecutor": AgentExecutor,
        "AgentInterface": AgentInterface,
        "AgentSkill": AgentSkill,
        "DefaultRequestHandler": DefaultRequestHandler,
        "InMemoryTaskStore": InMemoryTaskStore,
        "Starlette": Starlette,
        "TaskUpdater": TaskUpdater,
        "create_agent_card_routes": create_agent_card_routes,
        "create_jsonrpc_routes": create_jsonrpc_routes,
        "new_task_from_user_message": new_task_from_user_message,
        "new_text_part": new_text_part,
    }


def ensure_a2a_dependencies() -> None:
    """Raise a helpful error when the optional A2A dependencies are absent."""
    _a2a_imports()


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
):
    """Build an A2A JSON-RPC application for one database AI agent team."""
    if pool_max_size < 1:
        raise ValueError("pool_max_size must be at least 1")

    imports = _a2a_imports()
    agent_card = _build_agent_card(imports, team_name, public_url, description)
    executor = _build_executor(imports, team_name)
    handler = imports["DefaultRequestHandler"](
        agent_executor=executor,
        task_store=imports["InMemoryTaskStore"](),
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
            yield
        finally:
            await select_ai.async_disconnect()

    routes = imports["create_agent_card_routes"](agent_card)
    routes.extend(
        imports["create_jsonrpc_routes"](
            handler,
            rpc_url="/a2a/jsonrpc/",
            enable_v0_3_compat=True,
        )
    )
    return imports["Starlette"](routes=routes, lifespan=lifespan)


def _build_agent_card(imports, team_name, public_url, description):
    description = description or f"Oracle Database AI agent team {team_name}."
    endpoint = f"{public_url.rstrip('/')}/a2a/jsonrpc/"
    return imports["AgentCard"](
        name=team_name,
        description=description,
        version=__version__,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=imports["AgentCapabilities"](streaming=True),
        supported_interfaces=[
            imports["AgentInterface"](
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=endpoint,
            ),
            imports["AgentInterface"](
                protocol_binding="JSONRPC",
                protocol_version="0.3",
                url=endpoint,
            ),
        ],
        skills=[
            imports["AgentSkill"](
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


def _build_executor(imports, team_name):
    agent_executor = imports["AgentExecutor"]
    task_updater = imports["TaskUpdater"]
    new_task_from_user_message = imports["new_task_from_user_message"]
    new_text_part = imports["new_text_part"]
    conversation_ids = {}
    conversation_lock = Lock()

    async def get_database_conversation_id(task):
        """Create one Oracle conversation for each A2A context."""
        a2a_context_id = task.context_id or task.id
        async with conversation_lock:
            conversation_id = conversation_ids.get(a2a_context_id)
            if conversation_id:
                return conversation_id

            conversation = select_ai.AsyncConversation(
                attributes=select_ai.ConversationAttributes(
                    title=f"A2A {team_name}",
                    description=f"A2A context {a2a_context_id}",
                )
            )
            conversation_id = await conversation.create()
            conversation_ids[a2a_context_id] = conversation_id
            return conversation_id

    class DatabaseTeamExecutor(agent_executor):
        async def execute(self, context, event_queue):
            if context.current_task:
                task = context.current_task
            else:
                task = new_task_from_user_message(context.message)
                await event_queue.enqueue_event(task)

            updater = task_updater(
                event_queue=event_queue,
                task_id=task.id,
                context_id=task.context_id,
            )
            await updater.start_work()
            conversation_id = await get_database_conversation_id(task)
            result = await AsyncTeam(team_name=team_name).run(
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
            updater = task_updater(
                event_queue=event_queue,
                task_id=context.current_task.id,
                context_id=context.current_task.context_id,
            )
            await updater.cancel()

    return DatabaseTeamExecutor()
