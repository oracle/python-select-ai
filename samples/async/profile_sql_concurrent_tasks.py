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
    select_ai.create_pool_async(
        user=user,
        password=password,
        dsn=dsn,
        min_size=1,
        max_size=3,
        increment=1,
    )
    tasks = []
    try:
        async_profile = await select_ai.AsyncProfile(
            profile_name="async_oci_ai_profile",
        )
        # Each operation acquires its own connection from the pool.
        tasks = [
            asyncio.create_task(async_profile.show_sql("How many customers?")),
            asyncio.create_task(async_profile.run_sql("How many promotions?")),
            asyncio.create_task(
                async_profile.explain_sql("How many promotions?")
            ),
        ]
        for task in asyncio.as_completed(tasks):
            print(await task)
    finally:
        # Finish cancellation before closing connections, including on errors.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await select_ai.async_disconnect()


asyncio.run(main())
