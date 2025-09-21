# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/vector_index_update_attributes.py
#
# Update Vector index attributes
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_vector_index = select_ai.AsyncVectorIndex(
        index_name="test_vector_index",
    )

    # Use vector_index.set_attributes to update a multiple attributes
    updated_attributes = select_ai.OracleVectorIndexAttributes(
        refresh_rate=1450,
    )
    await async_vector_index.set_attributes(attributes=updated_attributes)

    # Use vector_index.set_attribute to update a single attribute
    await async_vector_index.set_attribute(
        attribute_name="similarity_threshold", attribute_value=0.5
    )
    attributes = await async_vector_index.get_attributes()
    print(attributes)


asyncio.run(main())
