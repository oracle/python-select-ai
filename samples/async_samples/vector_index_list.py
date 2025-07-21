# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    vector_index = select_ai.AsyncVectorIndex()
    async for index in vector_index.list(index_name_pattern="^test"):
        print("Vector index", index.index_name)
        print("Vector index profile", index.profile)


if __name__ == "__main__":
    asyncio.run(main())
