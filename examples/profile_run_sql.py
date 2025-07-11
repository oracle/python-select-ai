# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

# This example shows to get results of SQL
# specified using natural language prompt


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    profile = select_ai.Profile(profile_name="oci_ai_profile")
    profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    print(profile)
    prompts = [
        "How many promotions are there in the sh database?",
        "How many products are there in the sh database ?",
    ]
    for prompt in prompts:
        print("Prompt is: ", prompt)
        # profile.run_sql returns a pandas dataframe
        df = profile.run_sql(prompt=prompt)
        print(df.columns)
        print(df)


if __name__ == "__main__":
    main()
