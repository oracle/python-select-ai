# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/async/team_create.py
#
# Create a team for movie analyst and run it
# -----------------------------------------------------------------------------

import asyncio
import os
import uuid

import select_ai
from select_ai.agent import (
    AsyncTeam,
    TeamAttributes,
)

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
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
            prompt="Could you list the movies in the database?",
            params={"conversation_id": str(uuid.uuid4())},
        )
    )


asyncio.run(main())
