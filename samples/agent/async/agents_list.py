# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/agents_list.py
#
# List all AI agents
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai
from select_ai.agent import AsyncAgent


async def main():
    user = os.getenv("SELECT_AI_USER")
    password = os.getenv("SELECT_AI_PASSWORD")
    dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async for agent in AsyncAgent.list():
        print(agent.agent_name)


asyncio.run(main())
