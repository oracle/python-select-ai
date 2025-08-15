# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from typing import Mapping

import oracledb

from .db import async_cursor, cursor

__all__ = [
    "async_create_credential",
    "async_delete_credential",
    "create_credential",
    "delete_credential",
]


def _validate_credential(credential: Mapping[str, str]):
    valid_keys = {
        "credential_name",
        "username",
        "password",
        "user_ocid",
        "tenancy_ocid",
        "private_key",
        "fingerprint",
        "comments",
    }
    for k in credential.keys():
        if k.lower() not in valid_keys:
            raise ValueError(
                f"Invalid value {k}: {credential[k]} for credential object"
            )


async def async_create_credential(credential: Mapping, replace: bool = False):
    """
    Async API to create credential.

    Creates a credential object using DBMS_CLOUD.CREATE_CREDENTIAL. if replace
    is True, credential will be replaced if it already exists

    """
    _validate_credential(credential)
    async with async_cursor() as cr:
        try:
            await cr.callproc(
                "DBMS_CLOUD.CREATE_CREDENTIAL", keyword_parameters=credential
            )
        except oracledb.DatabaseError as e:
            (error,) = e.args
            # If already exists and replace is True then drop and recreate
            if error.code == 20022 and replace:
                await cr.callproc(
                    "DBMS_CLOUD.DROP_CREDENTIAL",
                    keyword_parameters={
                        "credential_name": credential["credential_name"]
                    },
                )
                await cr.callproc(
                    "DBMS_CLOUD.CREATE_CREDENTIAL",
                    keyword_parameters=credential,
                )
            else:
                raise


async def async_delete_credential(credential_name: str, force: bool = False):
    """
    Async API to create credential.

    Deletes a credential object using DBMS_CLOUD.DROP_CREDENTIAL
    """
    async with async_cursor() as cr:
        try:
            await cr.callproc(
                "DBMS_CLOUD.DROP_CREDENTIAL",
                keyword_parameters={"credential_name": credential_name},
            )
        except oracledb.DatabaseError as e:
            (error,) = e.args
            if error.code == 20004 and force:  # does not exist
                pass
            else:
                raise


def create_credential(credential: Mapping, replace: bool = False):
    """

    Creates a credential object using DBMS_CLOUD.CREATE_CREDENTIAL. if replace
    is True, credential will be replaced if it "already exists"

    """
    _validate_credential(credential)
    with cursor() as cr:
        try:
            cr.callproc(
                "DBMS_CLOUD.CREATE_CREDENTIAL", keyword_parameters=credential
            )
        except oracledb.DatabaseError as e:
            (error,) = e.args
            # If already exists and replace is True then drop and recreate
            if error.code == 20022 and replace:
                cr.callproc(
                    "DBMS_CLOUD.DROP_CREDENTIAL",
                    keyword_parameters={
                        "credential_name": credential["credential_name"]
                    },
                )
                cr.callproc(
                    "DBMS_CLOUD.CREATE_CREDENTIAL",
                    keyword_parameters=credential,
                )
            else:
                raise


def delete_credential(credential_name: str, force: bool = False):
    with cursor() as cr:
        try:
            cr.callproc(
                "DBMS_CLOUD.DROP_CREDENTIAL",
                keyword_parameters={"credential_name": credential_name},
            )
        except oracledb.DatabaseError as e:
            (error,) = e.args
            if error.code == 20004 and force:  # does not exist
                pass
            else:
                raise
