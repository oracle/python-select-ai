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

    oci_provider_attributes = select_ai.OCIGenAIProviderAttributes(
        model="meta.llama-3.1-70b-instruct"
    )
    profile = select_ai.Profile(
        profile_name="oci_ai_profile",
        attributes=oci_provider_attributes,
        description="MY OCI AI Profile",
        fetch_and_merge_attributes=True,
    )

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
    print(
        profile.generate_synthetic_data(
            synthetic_data_attributes=synthetic_data_attributes
        )
    )


if __name__ == "__main__":
    main()
