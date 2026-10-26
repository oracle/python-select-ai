# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# vector_index_create.py
#
# Create a vector index for Retrieval Augmented Generation (RAG)
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.environ["SELECT_AI_USER"]
password = os.environ["SELECT_AI_PASSWORD"]
dsn = os.environ["SELECT_AI_DB_CONNECT_STRING"]
# Upload samples/data/refund-policy.txt to your bucket, then set its URI.
source_uri = os.environ["SELECT_AI_DOCUMENT_URI"]
provider_credential = os.getenv(
    "SELECT_AI_PROVIDER_CREDENTIAL", "my_oci_ai_profile_key"
)
storage_credential = os.environ["SELECT_AI_OBJECT_STORAGE_CREDENTIAL"]

select_ai.connect(user=user, password=password, dsn=dsn)
try:
    provider = select_ai.OCIGenAIProvider(
        region=os.getenv("SELECT_AI_OCI_REGION", "us-chicago-1"),
        oci_apiformat="GENERIC",
        embedding_model=os.getenv(
            "SELECT_AI_EMBEDDING_MODEL", "cohere.embed-v4.0"
        ),
    )
    profile = select_ai.Profile(
        profile_name="oci_vector_ai_profile",
        attributes=select_ai.ProfileAttributes(
            credential_name=provider_credential,
            provider=provider,
        ),
        description="Profile for the sample refund policy",
        replace=True,
    )
    vector_index = select_ai.VectorIndex(
        index_name="test_vector_index",
        attributes=select_ai.OracleVectorIndexAttributes(
            location=source_uri,
            object_storage_credential_name=storage_credential,
        ),
        description="Sample refund policy",
        profile=profile,
    )
    vector_index.create(replace=True, wait_for_completion=True)
    print("Created vector index: test_vector_index")
finally:
    select_ai.disconnect()
