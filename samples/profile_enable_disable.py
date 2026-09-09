# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_enable_disable.py
#
# Disable and re-enable an existing Select AI profile.
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")

select_ai.connect(user=user, password=password, dsn=dsn)
profile = select_ai.Profile(profile_name=profile_name)

profile.disable()
try:
    print("Disabled profile:", profile.profile_name)
finally:
    profile.enable()
    print("Enabled profile:", profile.profile_name)
