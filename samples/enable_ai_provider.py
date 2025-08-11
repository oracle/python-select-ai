# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# enable_ai_provider.py
#
# Grants privileges to the database user and add ACL to invoke the AI Provider
# endpoint
# -----------------------------------------------------------------------------

import os

import select_ai

admin_user = os.getenv("SELECT_AI_ADMIN_USER")
password = os.getenv("SELECT_AI_ADMIN_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai_user = os.getenv("SELECT_AI_USER")

select_ai.connect(user=admin_user, password=password, dsn=dsn)
select_ai.enable_provider(
    users=select_ai_user, provider_endpoint="*.openai.azure.com"
)
print("Enabled AI provider for user: ", select_ai_user)
