# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/create_ai_credential.py
#
# Async API to create credential
# -----------------------------------------------------------------------------

import asyncio
import os

import oci
import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    default_config = oci.config.from_file()
    oci.config.validate_config(default_config)
    with open(default_config["key_file"]) as fp:
        key_contents = fp.read()
    credential = {
        "credential_name": "my_oci_ai_profile_key",
        "user_ocid": default_config["user"],
        "tenancy_ocid": default_config["tenancy"],
        "private_key": key_contents,
        "fingerprint": default_config["fingerprint"],
    }
    await select_ai.async_create_credential(
        credential=credential, replace=True
    )
    print("Created credential: ", credential["credential_name"])


asyncio.run(main())
