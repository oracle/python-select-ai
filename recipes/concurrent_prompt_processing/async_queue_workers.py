# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# concurrent_prompt_processing/async_queue_workers.py
#
# Process prompts with async queue workers.
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

pool_min = int(os.getenv("SELECT_AI_POOL_MIN", "1"))
pool_max = int(os.getenv("SELECT_AI_POOL_MAX", "4"))
pool_increment = int(os.getenv("SELECT_AI_POOL_INCREMENT", "1"))

profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "async_oci_ai_profile")
worker_count = int(os.getenv("SELECT_AI_WORKER_COUNT", str(pool_max)))

prompts = [
    "How many customers?",
    "How many products?",
    "How many promotions?",
    "List the top 5 customers by sales.",
]


async def worker(name, profile, queue, results):
    while True:
        item = await queue.get()
        try:
            if item is None:
                return

            index, prompt = item
            sql = await profile.show_sql(prompt=prompt)
            results[index] = (prompt, sql)
        finally:
            queue.task_done()


async def main():
    select_ai.create_pool_async(
        user=user,
        password=password,
        dsn=dsn,
        min_size=pool_min,
        max_size=pool_max,
        increment=pool_increment,
    )

    try:
        profile = await select_ai.AsyncProfile(profile_name=profile_name)
        queue = asyncio.Queue()
        results = [None] * len(prompts)

        workers = [
            asyncio.create_task(worker(i, profile, queue, results))
            for i in range(worker_count)
        ]

        for index, prompt in enumerate(prompts):
            await queue.put((index, prompt))

        for _ in workers:
            await queue.put(None)

        await queue.join()
        await asyncio.gather(*workers)

        for prompt, sql in results:
            print(f"\nPrompt: {prompt}")
            print(sql)
    finally:
        await select_ai.async_disconnect()


asyncio.run(main())
