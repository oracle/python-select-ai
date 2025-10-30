# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# tool_create.py
#
# Create an in-built SQL tool
# -----------------------------------------------------------------------------

import os
from pprint import pformat

import select_ai
import select_ai.agent

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

profile_attributes = select_ai.ProfileAttributes(
    credential_name="my_oci_ai_profile_key",
    object_list=[
        {"owner": user, "name": "MOVIE"},
        {"owner": user, "name": "ACTOR"},
        {"owner": user, "name": "DIRECTOR"},
    ],
    provider=select_ai.OCIGenAIProvider(
        region="us-chicago-1",
        oci_apiformat="GENERIC",
        model="meta.llama-4-maverick-17b-128e-instruct-fp8",
    ),
)
profile = select_ai.Profile(
    profile_name="LLAMA_4_MAVERICK",
    attributes=profile_attributes,
    description="MY OCI AI Profile",
    replace=True,
)

# Use the OCI AI Profile to perform natural
# language SQL translation
sql_tool = select_ai.agent.Tool.create_sql_tool(
    tool_name="MOVIE_SQL_TOOL",
    description="My Select AI MOVIE SQL agent tool",
    profile_name="LLAMA_4_MAVERICK",
    replace=True,
)
print(sql_tool.tool_name)
print(pformat(sql_tool.attributes))
