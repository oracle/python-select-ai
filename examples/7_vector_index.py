import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    if select_ai.is_connected():
        print("Connected to Database")
    else:
        raise Exception("Not connected to Database")

    profile = select_ai.Profile(
        profile_name="oci_ai_profile", fetch_and_merge_attributes=True
    )
    print("fetched profile: ", profile)

    vector_index_attributes = select_ai.VectorIndexAttributes(
        location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph",
        object_storage_credential_name="my_oci_ai_profile_key",
    )

    profile.create_vector_index(
        index_name="test_vector_index",
        attributes=vector_index_attributes,
        description="Vector index for conda environments",
        replace=True,
    )

    print("created vector index: test_vector_index")

    print("list vector indices")
    for vector_index in profile.list_vector_indexes(
        index_name_pattern="^test"
    ):
        print(vector_index)


if __name__ == "__main__":
    main()
