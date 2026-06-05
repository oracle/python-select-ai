# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# concurrent_prompt_processing/async_as_completed.py
#
# Process async prompt results as each task completes.
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

prompts = [
    "How many customers?",
    "How many products?",
    "How many promotions?",
    "List the top 5 customers by sales.",
]


async def show_sql(profile, prompt):
    sql = await profile.show_sql(prompt=prompt)
    return prompt, sql


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
        tasks = [show_sql(profile, prompt) for prompt in prompts]

        for task in asyncio.as_completed(tasks):
            prompt, sql = await task
            print(f"\nPrompt: {prompt}")
            print(sql)
    finally:
        await select_ai.async_disconnect()


asyncio.run(main())
