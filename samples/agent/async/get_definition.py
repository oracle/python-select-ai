# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/async/get_definition.py
#
# Create a temporary task and asynchronously print its PL/SQL definition.
# -----------------------------------------------------------------------------

import asyncio
import os
import uuid

import select_ai
from select_ai.agent import AsyncTask, TaskAttributes, async_get_definition

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    task = AsyncTask(
        task_name=f"SAMPLE_DEFINITION_TASK_{uuid.uuid4().hex.upper()}",
        attributes=TaskAttributes(
            instruction="Answer the user's question: {query}", tools=[]
        ),
    )
    await task.create(replace=True)

    try:
        print(await async_get_definition("TASK", task.task_name))
    finally:
        await task.delete(force=True)


asyncio.run(main())
