# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_gen_multi_table_synthetic_data.py
#
# Generate synthetic data for multiple tables in a single request
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)
profile = select_ai.Profile(profile_name="oci_ai_profile")
synthetic_data_params = select_ai.SyntheticDataParams(
    sample_rows=100, table_statistics=True, priority="HIGH"
)
object_list = [
    {
        "owner": user,
        "name": "MOVIE",
        "record_count": 100,
        "user_prompt": "the release date for the movies should be in 2019",
    },
    {"owner": user, "name": "ACTOR", "record_count": 10},
    {"owner": user, "name": "DIRECTOR", "record_count": 5},
]
synthetic_data_attributes = select_ai.SyntheticDataAttributes(
    object_list=object_list, params=synthetic_data_params
)
profile.generate_synthetic_data(
    synthetic_data_attributes=synthetic_data_attributes
)
