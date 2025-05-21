import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    oci_provider_attributes = select_ai.OCIGenAIProviderAttributes(
        model="meta.llama-3.1-70b-instruct"
    )
    profile = select_ai.Profile(
        profile_name="oci_ai_profile",
        attributes=oci_provider_attributes,
        description="MY OCI AI Profile",
        fetch_and_merge_attributes=True,
    )
    print(profile)
    print(profile.chat(prompt="What is OCI ?"))


if __name__ == "__main__":
    main()
