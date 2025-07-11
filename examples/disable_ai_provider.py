# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os

import select_ai

admin_user = os.getenv("SELECT_AI_ADMIN_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

# Add Users to enable AI profile privileges
db_users = ["SPARK_DB_USER"]


def main():
    select_ai.connect(user=admin_user, password=password, dsn=dsn)
    select_ai.disable_provider(
        users=db_users, provider_endpoint="*.openai.azure.com"
    )
    print("Disabled AI provider for user: ", db_users)


if __name__ == "__main__":
    main()
