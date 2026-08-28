# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Create an Azure OpenAI Select AI profile using only select_ai APIs.

Before running, source test.env. The script grants the required database HTTP
access, creates/replaces AZUREAI_CRED, and creates/replaces the profile.
"""

import os
from pprint import pformat

import select_ai

AZURE_HOST = "adbst-ai-resource-japan-east.openai.azure.com"
AZURE_RESOURCE = "ADBST-AI-RESOURCE-JAPAN-EAST"
AZURE_DEPLOYMENT = "ADBST-AI-RESOURCE-JAPAN-EAST-DEPLOYMENT"
AZURE_EMBEDDING_DEPLOYMENT = (
    "ADBST-AI-RESOURCE-JAPAN-EAST-text-embedding-3-large"
)
CREDENTIAL_NAME = "AZUREAI_CRED"
PROFILE_NAME = "azureai_prf"

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
        host=AZURE_HOST,
        privileges="http",
    )
finally:
    select_ai.disconnect()

select_ai.connect(user=app_user, password=app_password, dsn=dsn)
try:
    select_ai.create_credential(
        {
            "credential_name": CREDENTIAL_NAME,
            "username": "azure",
            "password": os.environ["AZURE_API_KEY"],
        },
        replace=True,
    )

    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        attributes=select_ai.ProfileAttributes(
            credential_name=CREDENTIAL_NAME,
            provider=select_ai.AzureProvider(
                azure_resource_name=AZURE_RESOURCE,
                azure_deployment_name=AZURE_DEPLOYMENT,
                azure_embedding_deployment_name=AZURE_EMBEDDING_DEPLOYMENT,
            ),
            object_list=[{"owner": app_user, "name": "CUSTOMERS"}],
            conversation=True,
            temperature=1,
            max_tokens=1500,
            seed=20,
        ),
        replace=True,
    )
    p = select_ai.Profile.fetch(profile_name=PROFILE_NAME)
    print(p)
    print("Created profile:", profile.profile_name)
    print(pformat(profile.get_attributes().dict(exclude_null=False)))
    print("Chat response:", profile.chat("Reply with: Azure chat succeeded."))
finally:
    select_ai.disconnect()
