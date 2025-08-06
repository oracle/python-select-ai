# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# profile_gen_single_table_synthetic_data.py
#
# Generate synthetic data for a single table
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
synthetic_data_attributes = select_ai.SyntheticDataAttributes(
    object_name="MOVIE",
    user_prompt="the release date for the movies should be in 2019",
    params=synthetic_data_params,
    record_count=100,
)
profile.generate_synthetic_data(
    synthetic_data_attributes=synthetic_data_attributes
)
