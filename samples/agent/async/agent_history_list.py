# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Asynchronously debug the latest execution of one agent team."""

import asyncio
import os
from pprint import pprint

import select_ai
from select_ai.agent import (
    AsyncTaskHistory,
    AsyncTeamHistory,
    AsyncToolHistory,
)

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
team_name = "ORACLE_AI_DATABASE_AGENT"


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    # Replace team_name with team_exec_id when the application has recorded it.
    async for team_run in AsyncTeamHistory.list(team_name=team_name, limit=1):
        pprint(team_run)

        # team_exec_id scopes the remaining history to the same execution.
        async for task_run in AsyncTaskHistory.list(
            team_exec_id=team_run.team_exec_id
        ):
            pprint(task_run)

        async for tool_run in AsyncToolHistory.list(
            team_exec_id=team_run.team_exec_id
        ):
            pprint(tool_run)


asyncio.run(main())
