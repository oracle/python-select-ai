# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_list.py
#
# List all the profile names matching a certain pattern
# -----------------------------------------------------------------------------

import os

import select_ai

select_ai.connect(
    user=os.environ["SELECT_AI_USER"],
    password=os.environ["SELECT_AI_PASSWORD"],
    dsn=os.environ["SELECT_AI_DB_CONNECT_STRING"],
)
try:
    for profile in select_ai.Profile.list():
        print(profile.qualified_name)
finally:
    select_ai.disconnect()
