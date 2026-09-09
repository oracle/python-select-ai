# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/sharing.py
#
# Inspect owner-qualified objects and grant/revoke access to shared objects
# using asynchronous APIs. The objects must already exist and the script must
# run as their owner.
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai
from select_ai.agent import AsyncTeam

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
owner = os.getenv("SELECT_AI_OWNER") or None
grantee = os.getenv("SELECT_AI_SHARE_GRANTEE")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "async_oci_ai_profile")
vector_index_name = os.getenv(
    "SELECT_AI_VECTOR_INDEX_NAME", "test_vector_index"
)
team_name = os.getenv("SELECT_AI_TEAM_NAME", "MOVIE_AGENT_TEAM")
credential_name = os.getenv(
    "SELECT_AI_CREDENTIAL_NAME", "my_oci_ai_profile_key"
)

if not grantee:
    raise RuntimeError(
        "Set SELECT_AI_SHARE_GRANTEE to a database user or role"
    )


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    profile = await select_ai.AsyncProfile.fetch(profile_name, owner=owner)
    profiles = [
        item
        async for item in select_ai.AsyncProfile.list(
            f"^{profile.profile_name}$",
            owner=profile.owner,
        )
    ]
    print("Profile:", profile.qualified_name)
    print("Profiles:", [item.qualified_name for item in profiles])
    await profile.grant_access(grantee)
    print("Granted profile access to:", grantee)
    await profile.revoke_access(grantee)
    print("Revoked profile access from:", grantee)

    vector_index = await select_ai.AsyncVectorIndex.fetch(
        vector_index_name,
        owner=owner,
    )
    indexes = [
        item
        async for item in select_ai.AsyncVectorIndex.list(
            f"^{vector_index.index_name}$",
            owner=vector_index.owner,
        )
    ]
    print("Vector index:", vector_index.qualified_name)
    print("Vector indexes:", [item.qualified_name for item in indexes])
    await vector_index.grant_access(grantee)
    print("Granted vector index access to:", grantee)
    await vector_index.revoke_access(grantee)
    print("Revoked vector index access from:", grantee)

    team = await AsyncTeam.fetch(team_name)
    await team.grant_access(grantee)
    print("Granted team access to:", grantee)
    await team.revoke_access(grantee)
    print("Revoked team access from:", grantee)

    await select_ai.async_grant_credential_access(credential_name, grantee)
    print("Granted credential access to:", grantee)
    await select_ai.async_revoke_credential_access(credential_name, grantee)
    print("Revoked credential access from:", grantee)


asyncio.run(main())
