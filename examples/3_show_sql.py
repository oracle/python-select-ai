import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)

    provider = select_ai.OCIGenAIProvider(
        region="us-chicago-1", oci_apiformat="GENERIC"
    )

    profile_attributes = select_ai.ProfileAttributes(
        credential_name="my_oci_ai_profile_key",
        object_list=[{"owner": "SH"}],
        provider=provider,
    )

    profile = select_ai.Profile(
        profile_name="oci_ai_profile",
        attributes=profile_attributes,
        description="MY OCI AI Profile",
        replace=True,
    )
    prompts = [
        "How many promotions are there in the sh database?",
        "How many products are there in the sh database ?",
    ]
    for prompt in prompts:
        print("Prompt is: ", prompt)
        print(profile.explain_sql(prompt=prompt))


if __name__ == "__main__":
    main()
