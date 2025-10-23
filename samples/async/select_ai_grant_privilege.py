# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/select_ai_grant_privilege.py
#
# Grant execute privileges on DBMS_CLOUD, DMBS_CLOUD_AI, DBMS_CLOUD_AI_AGENT
# and DBMS_CLOUD_PIPELINE PL/SQL packages
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
    await select_ai.async_grant_privileges(
        users=select_ai_user,
    )
    print("Granted privileges to: ", select_ai_user)


asyncio.run(main())
