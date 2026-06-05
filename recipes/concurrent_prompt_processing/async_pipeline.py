# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# concurrent_prompt_processing/async_pipeline.py
#
# Send multiple prompts in one database round trip using run_pipeline().
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

prompt_specifications = [
    ("How many customers?", select_ai.Action.SHOWSQL),
    ("How many promotions?", select_ai.Action.RUNSQL),
    ("Explain how to count products.", select_ai.Action.EXPLAINSQL),
]


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
        results = await profile.run_pipeline(
            prompt_specifications, continue_on_error=True
        )

        for (prompt, action), result in zip(prompt_specifications, results):
            print(f"\nPrompt: {prompt}")
            print(f"Action: {action}")
            print(result)
    finally:
        await select_ai.async_disconnect()


asyncio.run(main())
