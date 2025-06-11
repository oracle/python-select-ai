import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile"
    )

    vector_index_attributes = select_ai.VectorIndexAttributes(
        location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph",
        object_storage_credential_name="my_oci_ai_profile_key",
    )

    await async_profile.create_vector_index(
        index_name="test_vector_index",
        attributes=vector_index_attributes,
        description="Vector index for conda environments",
        replace=True,
    )
    print("created vector index: test_vector_index")

    async for vector_index in async_profile.list_vector_indexes(
        index_name_pattern="^test"
    ):
        print(vector_index)


if __name__ == "__main__":
    asyncio.run(main())
