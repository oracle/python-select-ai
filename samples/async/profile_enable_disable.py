# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/profile_enable_disable.py
#
# Asynchronously disable and re-enable an existing Select AI profile.
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    profile = await select_ai.AsyncProfile(profile_name=profile_name)

    await profile.disable()
    try:
        print("Disabled profile:", profile.profile_name)
    finally:
        await profile.enable()
        print("Enabled profile:", profile.profile_name)


asyncio.run(main())
