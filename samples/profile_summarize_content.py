# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_summarize.py
#
# Summarize the content
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

content = """
A gas cloud in our galaxy, Sagittarius B2, contains enough alcohol to brew 400
trillion pints of beer, and some stars are so cool that you could touch them
without being burned. Meanwhile, on the exoplanet 55 Cancri e, a form of
"hot ice" exists where high pressure prevents water from becoming gas even at
high temperatures. Additionally, some ancient stars found in the Milky Way's
halo are much older than the Sun, providing clues about the early universe and
its composition
"""

select_ai.connect(user=user, password=password, dsn=dsn)
profile = select_ai.Profile(profile_name="oci_ai_profile")
summary = profile.summarize(content=content)
print(summary)
