# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Create an AWS Bedrock Select AI profile using only select_ai APIs.

Before running, source test.env. The script grants the required database HTTP
access, creates/replaces AWS_CRED, and creates/replaces the profile.
"""

import os
from pprint import pformat

import select_ai

AWS_HOST = "bedrock-runtime.us-east-1.amazonaws.com"
CREDENTIAL_NAME = "AWS_CRED"
PROFILE_NAME = "aws_bedrock_meta_prf"

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
        host=AWS_HOST,
        privileges="http",
    )
finally:
    select_ai.disconnect()

select_ai.connect(user=app_user, password=app_password, dsn=dsn)
try:
    select_ai.create_credential(
        {
            "credential_name": CREDENTIAL_NAME,
            "username": os.environ["AWS_ACCESS_KEY_ID"],
            "password": os.environ["AWS_SECRET_ACCESS_KEY"],
        },
        replace=True,
    )

    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        attributes=select_ai.ProfileAttributes(
            credential_name=CREDENTIAL_NAME,
            provider=select_ai.AWSProvider(
                region="us-east-1",
                model="meta.llama3-70b-instruct-v1:0",
                embedding_model="amazon.titan-embed-text-v1",
            ),
            object_list=[{"owner": app_user, "name": "CUSTOMERS"}],
            conversation=True,
            temperature=1,
            max_tokens=1500,
        ),
        replace=True,
    )

    print("Created profile:", profile.profile_name)
    print(pformat(profile.get_attributes().dict(exclude_null=False)))
    print("Chat response:", profile.chat("Reply with: AWS chat succeeded."))
finally:
    select_ai.disconnect()
