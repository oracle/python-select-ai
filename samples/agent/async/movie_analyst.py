# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/agent/movie_analyst.py
#
# Demonstrates movie analyst AI agent
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


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    # Agent
    agent = AsyncAgent(
        agent_name="MOVIE_ANALYST",
        attributes=AgentAttributes(
            profile_name="oci_ai_profile",
            role="You are an AI Movie Analyst. "
            "Your can help answer a variety of questions related to movies. ",
            enable_human_tool=False,
        ),
    )
    await agent.create(enabled=True, replace=True)
    print("Create Agent", agent)

    # Task
    task = AsyncTask(
        task_name="ANALYZE_MOVIE_TASK",
        description="Movie task involving a human",
        attributes=TaskAttributes(
            instruction="Help the user with their request about movies. "
            "User question: {query}",
            enable_human_tool=False,
        ),
    )
    await task.create(replace=True)
    print("Created Task", task)

    # Team
    team = AsyncTeam(
        team_name="MOVIE_AGENT_TEAM",
        attributes=TeamAttributes(
            agents=[{"name": "MOVIE_ANALYST", "task": "ANALYZE_MOVIE_TASK"}],
            process="sequential",
        ),
    )
    await team.create(enabled=True, replace=True)
    print(
        await team.run(
            prompt="In the movie Titanic, was there enough space for Jack ? ",
            params={"conversation_id": str(uuid.uuid4())},
        )
    )


asyncio.run(main())
