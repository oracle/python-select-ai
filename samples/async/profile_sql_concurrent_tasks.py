# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/profile_sql_concurrent_tasks.py
#
# Demonstrates sending multiple prompts concurrently using asyncio
# -----------------------------------------------------------------------------


import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
    )
    sql_tasks = [
        async_profile.show_sql(prompt="How many customers?"),
        async_profile.run_sql(prompt="How many promotions?"),
        async_profile.explain_sql(prompt="How many promotions?"),
    ]

    # Collect results from multiple asynchronous tasks
    for sql_task in asyncio.as_completed(sql_tasks):
        result = await sql_task
        print(result)


asyncio.run(main())
