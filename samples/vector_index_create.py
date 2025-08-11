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

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


select_ai.connect(user=user, password=password, dsn=dsn)
# Configure an AI provider with an embedding model
# of your choice
provider = select_ai.OCIGenAIProvider(
    region="us-chicago-1",
    oci_apiformat="GENERIC",
    embedding_model="cohere.embed-english-v3.0",
)

# Create an AI profile to use the Vector index with
profile_attributes = select_ai.ProfileAttributes(
    credential_name="my_oci_ai_profile_key",
    provider=provider,
)
profile = select_ai.Profile(
    profile_name="oci_vector_ai_profile",
    attributes=profile_attributes,
    description="MY OCI AI Profile",
    replace=True,
)

# Specify objects to create an embedding for. In this example,
# the objects reside in ObjectStore and the vector database is
# Oracle
vector_index_attributes = select_ai.OracleVectorIndexAttributes(
    location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph",
    object_storage_credential_name="my_oci_ai_profile_key",
)

# Create a Vector index object
vector_index = select_ai.VectorIndex(
    index_name="test_vector_index",
    attributes=vector_index_attributes,
    description="Test vector index",
    profile=profile,
)
vector_index.create(replace=True)
print("Created vector index: test_vector_index")
