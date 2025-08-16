# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/vector_index_create.py
#
# Create a vector index for Retrieval Augmented Generation (RAG)
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    provider = select_ai.OCIGenAIProvider(
        region="us-chicago-1",
        oci_apiformat="GENERIC",
        embedding_model="cohere.embed-english-v3.0",
    )
    profile_attributes = select_ai.ProfileAttributes(
        credential_name="my_oci_ai_profile_key",
        provider=provider,
    )
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_vector_ai_profile",
        attributes=profile_attributes,
        description="MY OCI AI Profile",
        replace=True,
    )

    vector_index_attributes = select_ai.OracleVectorIndexAttributes(
        location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph",
        object_storage_credential_name="my_oci_ai_profile_key",
    )

    async_vector_index = select_ai.AsyncVectorIndex(
        index_name="test_vector_index",
        attributes=vector_index_attributes,
        description="Vector index for conda environments",
        profile=async_profile,
    )
    await async_vector_index.create(replace=True)
    print("Created vector index: test_vector_index")


asyncio.run(main())
