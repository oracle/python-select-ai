import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    oci_provider_attributes = select_ai.OCIGenAIProviderAttributes(
        region="us-chicago-1",
        credential_name="my_oci_ai_profile_key",
        oci_apiformat="GENERIC",
        object_list=[{"owner": "SH"}],
    )
    profile = select_ai.Profile(
        profile_name="oci_ai_profile",
        attributes=oci_provider_attributes,
        description="MY OCI AI Profile",
        replace=True,
    )
    # profile.set_attributes(attributes=oci_provider_attributes)
    profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    prompts = [
        "How many promotions are there in the sh database?",
        "How many products are there in the sh database ?",
    ]
    for prompt in prompts:
        print("Prompt is: ", prompt)
        df = profile.run_sql(prompt=prompt)
        print(df.columns)
        print(df)


if __name__ == "__main__":
    main()
