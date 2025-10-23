# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# select_ai_grant_privilege.py
#
# Grant execute privileges on DBMS_CLOUD, DMBS_CLOUD_AI, DBMS_CLOUD_AI_AGENT
# and DBMS_CLOUD_PIPELINE PL/SQL packages
# -----------------------------------------------------------------------------

import os

import select_ai

admin_user = os.getenv("SELECT_AI_ADMIN_USER")
password = os.getenv("SELECT_AI_ADMIN_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai_user = os.getenv("SELECT_AI_USER")


select_ai.connect(user=admin_user, password=password, dsn=dsn)
select_ai.grant_privileges(users=select_ai_user)
print("Granted privileges to: ", select_ai_user)
