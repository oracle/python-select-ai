# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# agent/async/task_create.py
#
# Create an AI agent task which uses SQL tool to perform NL2SQL
# -----------------------------------------------------------------------------

import asyncio
import os
from pprint import pformat

import select_ai
import select_ai.agent
from select_ai.agent import AsyncTask, TaskAttributes

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    task = AsyncTask(
        task_name="ANALYZE_MOVIE_TASK",
        description="Search for movies in the database",
        attributes=TaskAttributes(
            instruction="Help the user with their request about movies. "
            "User question: {query}. "
            "You can use SQL tool to search the data from database",
            tools=["MOVIE_SQL_TOOL"],
            enable_human_tool=False,
        ),
    )
    await task.create(replace=True)
    print(task.task_name)
    print(pformat(task.attributes))


asyncio.run(main())
