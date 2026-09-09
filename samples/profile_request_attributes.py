# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_request_attributes.py
#
# Override profile attributes for one request without changing the saved
# profile.
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")

select_ai.connect(user=user, password=password, dsn=dsn)
profile = select_ai.Profile(profile_name=profile_name)

instruction = "Include the exact marker PYSAI_REQUEST_ATTRIBUTES_SAMPLE."
request_attributes = {
    "additional_instructions": instruction,
    "seed": 42,
    "source_language": "en",
    "target_language": "de",
}

prompt = profile.show_prompt(
    prompt="Tell me about Oracle Cloud Infrastructure.",
    attributes=request_attributes,
)
print("Request attributes applied:", instruction in prompt)
