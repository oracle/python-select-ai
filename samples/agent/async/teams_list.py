# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# agent/async/teams_list.py
#
# List all teams saved in the database
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai
from select_ai.agent import AsyncTeam

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async for team in AsyncTeam.list():
        print(team.team_name)


asyncio.run(main())
