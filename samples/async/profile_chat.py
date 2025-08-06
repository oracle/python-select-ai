# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/profile_chat.py
#
# Chat using an AI Profile
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
        profile_name="async_oci_ai_profile"
    )

    # Asynchronously send multiple chat prompts
    chat_tasks = [
        async_profile.chat(prompt="What is OCI ?"),
        async_profile.chat(prompt="What is OML4PY?"),
        async_profile.chat(prompt="What is Autonomous Database ?"),
    ]
    for chat_task in asyncio.as_completed(chat_tasks):
        result = await chat_task
        print(result)


asyncio.run(main())
