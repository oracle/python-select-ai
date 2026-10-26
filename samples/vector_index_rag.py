# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# vector_index_rag.py
#
# Demonstrates Retrieval Augmented Generation (RAG) using ai_profile.narrate()
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.environ["SELECT_AI_USER"]
password = os.environ["SELECT_AI_PASSWORD"]
dsn = os.environ["SELECT_AI_DB_CONNECT_STRING"]

select_ai.connect(user=user, password=password, dsn=dsn)
try:
    profile = select_ai.Profile(profile_name="oci_vector_ai_profile")
    response = profile.narrate(
        "How many days do customers have to request a refund?"
    )
    print(response)
finally:
    select_ai.disconnect()
