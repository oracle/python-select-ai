# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/vector_index_rag.py
#
# Demonstrates Retrieval Augmented Generation (RAG) using ai_profile.narrate()
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.environ["SELECT_AI_USER"]
password = os.environ["SELECT_AI_PASSWORD"]
dsn = os.environ["SELECT_AI_DB_CONNECT_STRING"]


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    try:
        profile = await select_ai.AsyncProfile(
            profile_name="async_oci_vector_ai_profile"
        )
        response = await profile.narrate(
            "How many days do customers have to request a refund?"
        )
        print(response)
    finally:
        await select_ai.async_disconnect()


asyncio.run(main())
