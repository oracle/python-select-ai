# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/profile_list.py
#
# List all the profile names matching a certain pattern
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai


async def main():
    await select_ai.async_connect(
        user=os.environ["SELECT_AI_USER"],
        password=os.environ["SELECT_AI_PASSWORD"],
        dsn=os.environ["SELECT_AI_DB_CONNECT_STRING"],
    )
    try:
        async for profile in select_ai.AsyncProfile.list():
            print(profile.qualified_name)
    finally:
        await select_ai.async_disconnect()


asyncio.run(main())
