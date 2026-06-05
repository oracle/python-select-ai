# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# revoke_network_access.py
#
# Remove a network ACL entry for host access
# -----------------------------------------------------------------------------

import os

import select_ai

admin_user = os.getenv("SELECT_AI_ADMIN_USER")
password = os.getenv("SELECT_AI_ADMIN_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai_user = os.getenv("SELECT_AI_USER")

select_ai.connect(user=admin_user, password=password, dsn=dsn)
select_ai.revoke_network_access(
    users=select_ai_user,
    host="smtp.example.com",
    privileges=["connect", "smtp"],
    lower_port=587,
    upper_port=587,
)
print("Revoked network access from: ", select_ai_user)
