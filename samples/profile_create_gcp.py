# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Create a Google Gemini Select AI profile using only select_ai APIs.

Before running, source test.env. The script grants the required database HTTP
access, creates/replaces GOOGLE_CRED, and creates/replaces the profile.
"""

import os
from pprint import pformat

import select_ai

GCP_HOST = "generativelanguage.googleapis.com"
CREDENTIAL_NAME = "GOOGLE_CRED"
PROFILE_NAME = "google_gemini_3_6_flash"

admin_user = os.environ["SELECT_AI_ADMIN_USER"]
admin_password = os.environ["SELECT_AI_ADMIN_PASSWORD"]
app_user = os.environ["SELECT_AI_USER"]
app_password = os.environ["SELECT_AI_PASSWORD"]
dsn = os.environ["SELECT_AI_DB_CONNECT_STRING"]

# Equivalent to DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(..., 'http').
select_ai.connect(user=admin_user, password=admin_password, dsn=dsn)
try:
    select_ai.grant_network_access(
        users=app_user,
        host=GCP_HOST,
        privileges="http",
    )
finally:
    select_ai.disconnect()

select_ai.connect(user=app_user, password=app_password, dsn=dsn)
try:
    select_ai.create_credential(
        {
            "credential_name": CREDENTIAL_NAME,
            "username": "GOOGLE",
            "password": os.environ["GOOGLE_API_KEY"],
        },
        replace=True,
    )

    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        attributes=select_ai.ProfileAttributes(
            credential_name=CREDENTIAL_NAME,
            provider=select_ai.GoogleProvider(
                embedding_model="gemini-embedding-001",
                model="gemini-3.6-flash",
            ),
            temperature=1,
            max_tokens=1500,
            seed=20,
        ),
        replace=True,
    )

    print("Created profile:", profile.profile_name)
    print(pformat(profile.get_attributes().dict(exclude_null=False)))
    print("Chat response:", profile.chat("Reply with: GCP chat succeeded."))
finally:
    select_ai.disconnect()
