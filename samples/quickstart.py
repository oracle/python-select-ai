# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Create a temporary OpenAI profile, query sample data, and clean up.

Use --setup to grant package privileges and OpenAI HTTP access as admin.
"""

import argparse
import os
import uuid

import select_ai

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--setup",
    action="store_true",
    help="Grant package privileges and OpenAI HTTP access as administrator",
)
args = parser.parse_args()

user = os.environ["SELECT_AI_USER"]
password = os.environ["SELECT_AI_PASSWORD"]
dsn = os.environ["SELECT_AI_DB_CONNECT_STRING"]
api_key = os.environ["OPENAI_API_KEY"]
model = os.environ["SELECT_AI_MODEL"]

if args.setup:
    print("Connecting as administrator...", flush=True)
    select_ai.connect(
        user=os.environ["SELECT_AI_ADMIN_USER"],
        password=os.environ["SELECT_AI_ADMIN_PASSWORD"],
        dsn=dsn,
        tcp_connect_timeout=15,
    )
    try:
        with select_ai.cursor() as cursor:
            cursor.connection.call_timeout = 120_000
            print(
                f"Granting Select AI package privileges to {user}...",
                flush=True,
            )
            select_ai.grant_privileges(users=user)
            print(
                f"Granting {user} HTTP access to api.openai.com...", flush=True
            )
            select_ai.grant_network_access(
                users=user, host="api.openai.com", privileges="http"
            )
            cursor.connection.commit()
    finally:
        select_ai.disconnect()

suffix = uuid.uuid4().hex[:12].upper()
table_name = f"SDK_DEMO_{suffix}"
credential_name = f"SDK_CRED_{suffix}"
profile_name = f"SDK_PROFILE_{suffix}"

print(f"Connecting as application user {user}...", flush=True)
select_ai.connect(
    user=user, password=password, dsn=dsn, tcp_connect_timeout=15
)

table_created = credential_created = profile_created = False
try:
    # This identifier is generated locally, rather than supplied by a caller.
    with select_ai.cursor() as cursor:
        cursor.connection.call_timeout = 120_000
        cursor.execute(
            "SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL"
        )
        owner = cursor.fetchone()[0]
        print("Creating the sample table...", flush=True)
        cursor.execute(
            f"CREATE TABLE {table_name} (id NUMBER PRIMARY KEY, name VARCHAR2(40))"
        )
        table_created = True
        cursor.executemany(
            f"INSERT INTO {table_name} (id, name) VALUES (:1, :2)",
            [(1, "Notebook"), (2, "Keyboard"), (3, "Monitor")],
        )
        cursor.connection.commit()

    print("Creating the OpenAI credential and profile...", flush=True)
    select_ai.create_credential(
        {
            "credential_name": credential_name,
            "username": "openai",
            "password": api_key,
        }
    )
    credential_created = True
    profile = select_ai.Profile(
        profile_name=profile_name,
        attributes=select_ai.ProfileAttributes(
            provider=select_ai.OpenAIProvider(model=model),
            credential_name=credential_name,
            object_list=[{"owner": owner, "name": table_name}],
        ),
    )
    profile_created = True

    prompt = (
        f"How many rows are in {table_name}? Return the count as ITEM_COUNT."
    )
    print("Generating SQL with OpenAI...", flush=True)
    print("Generated SQL:", profile.show_sql(prompt), flush=True)
    # run_sql generates and executes a fresh response to the prompt.
    print("Generating and executing the query with OpenAI...", flush=True)
    print(profile.run_sql(prompt))
finally:
    print(
        "Removing temporary objects and closing the connection...", flush=True
    )
    # Attempt each cleanup even if an earlier cleanup fails.
    try:
        if profile_created:
            select_ai.Profile.delete_profile(profile_name, force=True)
    finally:
        try:
            if credential_created:
                select_ai.delete_credential(credential_name, force=True)
        finally:
            try:
                if table_created:
                    with select_ai.cursor() as cursor:
                        cursor.execute(f"DROP TABLE {table_name} PURGE")
            finally:
                select_ai.disconnect()
