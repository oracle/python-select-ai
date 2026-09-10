# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/async/team_supervisor_inspect.py
#
# Async version of the supervised team creation, execution, and inspection
# sample.
# Uses SELECT_AI_PROFILE_NAME when set; otherwise uses oci_ai_profile.
# -----------------------------------------------------------------------------

import asyncio
import os
import uuid

import select_ai
from select_ai.agent import (
    AgentAttributes,
    AsyncAgent,
    AsyncTask,
    AsyncTeam,
    TaskAttributes,
    TeamAttributes,
)
from select_ai.conversation import (
    AsyncConversation,
    ConversationAttributes,
)

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")


async def main():
    suffix = uuid.uuid4().hex.upper()
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    task = AsyncTask(
        task_name=f"SAMPLE_TASK_{suffix}",
        attributes=TaskAttributes(
            instruction="Answer the user's question: {query}",
            tools=[],
            enable_human_tool=False,
        ),
    )
    worker = AsyncAgent(
        agent_name=f"SAMPLE_WORKER_{suffix}",
        attributes=AgentAttributes(
            profile_name=profile_name,
            role="You answer user questions.",
            enable_human_tool=False,
        ),
    )
    supervisor = AsyncAgent(
        agent_name=f"SAMPLE_SUPERVISOR_{suffix}",
        attributes=AgentAttributes(
            profile_name=profile_name,
            role="You supervise and coordinate the team.",
            enable_human_tool=False,
            supervisor=True,
        ),
    )
    team = AsyncTeam(
        team_name=f"SAMPLE_TEAM_{suffix}",
        attributes=TeamAttributes(
            agents=[{"name": worker.agent_name, "task": task.task_name}],
            process="sequential",
            supervisor_agent=supervisor.agent_name,
        ),
    )

    conversation = AsyncConversation(
        attributes=ConversationAttributes(
            title="Supervised team sample",
            description="Conversation for the supervised team sample",
        )
    )

    created_objects = []
    conversation_created = False
    try:
        await task.create(replace=True)
        created_objects.append(task)
        await worker.create(replace=True)
        created_objects.append(worker)
        await supervisor.create(replace=True)
        created_objects.append(supervisor)
        await team.create(replace=True)
        created_objects.append(team)

        await conversation.create()
        conversation_created = True
        response = await team.run(
            prompt="What is the capital of France? Answer in one sentence.",
            params={"conversation_id": conversation.conversation_id},
        )
        if response is None or (
            isinstance(response, str) and response.startswith("Task failed:")
        ):
            raise RuntimeError(f"Supervised team run failed: {response}")
        print("Team response:", response)

        fetched = await AsyncTeam.fetch(team.team_name)
        print("Supervisor agent:", fetched.attributes.supervisor_agent)
        print("Supervisor task:", fetched.attributes.supervisor_task)
        print("Team description:", await team.describe_team())
        print("Team tools:", await team.list_tools())
    finally:
        if conversation_created:
            await conversation.delete(force=True)
        for obj in reversed(created_objects):
            await obj.delete(force=True)


asyncio.run(main())
