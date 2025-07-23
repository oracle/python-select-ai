# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from typing import List, Mapping, Union

import oracledb

from .db import cursor
from .sql import (
    DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
    ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
    GRANT_PRIVILEGES_TO_USER,
    REVOKE_PRIVILEGES_FROM_USER,
)

__all__ = [
    "create_credential",
    "disable_provider",
    "enable_provider",
]


def create_credential(credential: Mapping, replace: bool = False):
    """
    Creates a credential object using DBMS_CLOUD.CREATE_CREDENTIAL

    if replace is True, credential will be replaced if it "already exists"

    """
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

    with cursor() as cr:
        try:
            cr.callproc(
                "DBMS_CLOUD.CREATE_CREDENTIAL", keyword_parameters=credential
            )
        except oracledb.DatabaseError as e:
            (error,) = e.args
            # If already exists and replace is True then drop and recreate
            if "already exists" in error.message.lower() and replace:
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


def enable_provider(
    users: Union[str, List[str]], provider_endpoint: str = None
):
    """
    Enables AI profile for the user. This method grants execute privilege
    on the packages DBMS_CLOUD, DBMS_CLOUD_AI and DBMS_CLOUD_PIPELINE. It
    also enables the user to invoke the AI(LLM) endpoint hosted at a
    certain domain
    """
    if isinstance(users, str):
        users = [users]

    with cursor() as cr:
        for user in users:
            cr.execute(GRANT_PRIVILEGES_TO_USER.format(user))
            if provider_endpoint:
                cr.execute(
                    ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
                    user=user,
                    host=provider_endpoint,
                )


def disable_provider(
    users: Union[str, List[str]], provider_endpoint: str = None
):
    """
    Disables AI provider for the user. This method revokes execute privilege
    on the packages DBMS_CLOUD, DBMS_CLOUD_AI and DBMS_CLOUD_PIPELINE. It
    also disables the user to invoke the AI(LLM) endpoint hosted at a
    certain domain
    """
    if isinstance(users, str):
        users = [users]

    with cursor() as cr:
        for user in users:
            cr.execute(REVOKE_PRIVILEGES_FROM_USER.format(user))
            if provider_endpoint:
                cr.execute(
                    DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
                    user=user,
                    host=provider_endpoint,
                )
