# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/vector_index_fetch.py
#
# Get vector index attributes
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_vector_index = await select_ai.AsyncVectorIndex.fetch(
        index_name="test_vector_index"
    )
    print(async_vector_index.attributes)
    print(async_vector_index.profile)


asyncio.run(main())
