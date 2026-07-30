# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/async/team_supervisor_inspect.py
#
# Async version of the supervised team creation and inspection sample.
# Requires SELECT_AI_PROFILE_NAME to name an existing AI profile.
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

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "LLAMA_4_MAVERICK")


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

    await task.create(replace=True)
    await worker.create(replace=True)
    await supervisor.create(replace=True)
    await team.create(replace=True)

    try:
        fetched = await AsyncTeam.fetch(team.team_name)
        print("Supervisor agent:", fetched.attributes.supervisor_agent)
        print("Supervisor task:", fetched.attributes.supervisor_task)
        print("Team description:", await team.describe_team())
        print("Team tools:", await team.list_tools())
    finally:
        await team.delete(force=True)
        await supervisor.delete(force=True)
        await worker.delete(force=True)
        await task.delete(force=True)


asyncio.run(main())
