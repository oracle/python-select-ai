# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/grant_network_access.py
#
# Add a network ACL entry for host access
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

admin_user = os.getenv("SELECT_AI_ADMIN_USER")
password = os.getenv("SELECT_AI_ADMIN_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai_user = os.getenv("SELECT_AI_USER")


async def main():
    await select_ai.async_connect(user=admin_user, password=password, dsn=dsn)
    await select_ai.async_grant_network_access(
        users=select_ai_user,
        host="smtp.example.com",
        privileges=["connect", "smtp"],
        lower_port=587,
        upper_port=587,
    )
    print("Granted network access to: ", select_ai_user)


asyncio.run(main())
