# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# sharing.py
#
# Inspect owner-qualified objects and grant/revoke access to shared objects.
# The objects must already exist and the script must run as their owner.
# -----------------------------------------------------------------------------

import os

import select_ai
from select_ai.agent import Team

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
owner = os.getenv("SELECT_AI_OWNER") or None
grantee = os.getenv("SELECT_AI_SHARE_GRANTEE")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")
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

select_ai.connect(user=user, password=password, dsn=dsn)

profile = select_ai.Profile.fetch(profile_name, owner=owner)
profiles = list(
    select_ai.Profile.list(
        f"^{profile.profile_name}$",
        owner=profile.owner,
    )
)
print("Profile:", profile.qualified_name)
print("Profiles:", [item.qualified_name for item in profiles])
profile.grant_access(grantee)
print("Granted profile access to:", grantee)
profile.revoke_access(grantee)
print("Revoked profile access from:", grantee)

vector_index = select_ai.VectorIndex.fetch(
    vector_index_name,
    owner=owner,
)
indexes = list(
    select_ai.VectorIndex.list(
        f"^{vector_index.index_name}$",
        owner=vector_index.owner,
    )
)
print("Vector index:", vector_index.qualified_name)
print("Vector indexes:", [item.qualified_name for item in indexes])
vector_index.grant_access(grantee)
print("Granted vector index access to:", grantee)
vector_index.revoke_access(grantee)
print("Revoked vector index access from:", grantee)

team = Team.fetch(team_name)
team.grant_access(grantee)
print("Granted team access to:", grantee)
team.revoke_access(grantee)
print("Revoked team access from:", grantee)

select_ai.grant_credential_access(credential_name, grantee)
print("Granted credential access to:", grantee)
select_ai.revoke_credential_access(credential_name, grantee)
print("Revoked credential access from:", grantee)
