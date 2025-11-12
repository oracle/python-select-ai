# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# agent/async/tasks_list.py
#
# List all tasks saved in the database
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai
from select_ai.agent import AsyncTask

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async for task in AsyncTask.list():
        print(task.task_name)


asyncio.run(main())
