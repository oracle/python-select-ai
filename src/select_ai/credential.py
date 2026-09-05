# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from typing import Mapping

import oracledb

from ._validations import validate_user_or_role_name
from .db import async_cursor, cursor

__all__ = [
    "async_create_credential",
    "async_delete_credential",
    "async_grant_credential_access",
    "async_revoke_credential_access",
    "create_credential",
    "delete_credential",
    "grant_credential_access",
    "revoke_credential_access",
]


_CREATE_PUBLIC_CREDENTIAL_SYNONYM = """
DECLARE
    v_credential_name VARCHAR2(261);
    v_owner VARCHAR2(261);
BEGIN
    v_credential_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:credential_name)),
        FALSE
    );
    v_owner := DBMS_ASSERT.ENQUOTE_NAME(
        SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'),
        FALSE
    );
    EXECUTE IMMEDIATE
        'CREATE OR REPLACE PUBLIC SYNONYM ' || v_credential_name ||
        ' FOR ' || v_owner || '.' || v_credential_name;
END;
"""

_DROP_PUBLIC_CREDENTIAL_SYNONYM = """
DECLARE
    v_credential_name VARCHAR2(261);
BEGIN
    v_credential_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:credential_name)),
        FALSE
    );
    EXECUTE IMMEDIATE 'DROP PUBLIC SYNONYM ' || v_credential_name;
END;
"""

_GRANT_CREDENTIAL_ACCESS = """
DECLARE
    v_credential_name VARCHAR2(261);
    v_owner VARCHAR2(261);
    v_user_or_role_name VARCHAR2(261);
BEGIN
    v_credential_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:credential_name)),
        FALSE
    );
    v_owner := DBMS_ASSERT.ENQUOTE_NAME(
        SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'),
        FALSE
    );
    v_user_or_role_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:user_or_role_name)),
        FALSE
    );
    EXECUTE IMMEDIATE
        'GRANT EXECUTE ON ' || v_owner || '.' || v_credential_name ||
        ' TO ' || v_user_or_role_name;
END;
"""

_REVOKE_CREDENTIAL_ACCESS = """
DECLARE
    v_credential_name VARCHAR2(261);
    v_owner VARCHAR2(261);
    v_user_or_role_name VARCHAR2(261);
BEGIN
    v_credential_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:credential_name)),
        FALSE
    );
    v_owner := DBMS_ASSERT.ENQUOTE_NAME(
        SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA'),
        FALSE
    );
    v_user_or_role_name := DBMS_ASSERT.ENQUOTE_NAME(
        DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER(:user_or_role_name)),
        FALSE
    );
    EXECUTE IMMEDIATE
        'REVOKE EXECUTE ON ' || v_owner || '.' || v_credential_name ||
        ' FROM ' || v_user_or_role_name;
END;
"""


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
            raise ValueError(f"Invalid key {k} for credential object")


async def async_grant_credential_access(
    credential_name: str,
    user_or_role_name: str,
) -> None:
    """Grant a database user or role access to a credential.

    :param str credential_name: Name of the credential in the current schema.
    :param str user_or_role_name: Database user or role receiving access.
    :return: None
    :raises: oracledb.DatabaseError
    """
    user_or_role_name = validate_user_or_role_name(user_or_role_name)
    async with async_cursor() as cr:
        await cr.execute(
            _GRANT_CREDENTIAL_ACCESS,
            credential_name=credential_name,
            user_or_role_name=user_or_role_name,
        )


async def async_revoke_credential_access(
    credential_name: str,
    user_or_role_name: str,
) -> None:
    """Revoke a database user or role's access to a credential.

    :param str credential_name: Name of the credential in the current schema.
    :param str user_or_role_name: Database user or role losing access.
    :return: None
    :raises: oracledb.DatabaseError
    """
    user_or_role_name = validate_user_or_role_name(user_or_role_name)
    async with async_cursor() as cr:
        await cr.execute(
            _REVOKE_CREDENTIAL_ACCESS,
            credential_name=credential_name,
            user_or_role_name=user_or_role_name,
        )


def grant_credential_access(
    credential_name: str,
    user_or_role_name: str,
) -> None:
    """Grant a database user or role access to a credential.

    :param str credential_name: Name of the credential in the current schema.
    :param str user_or_role_name: Database user or role receiving access.
    :return: None
    :raises: oracledb.DatabaseError
    """
    user_or_role_name = validate_user_or_role_name(user_or_role_name)
    with cursor() as cr:
        cr.execute(
            _GRANT_CREDENTIAL_ACCESS,
            credential_name=credential_name,
            user_or_role_name=user_or_role_name,
        )


def revoke_credential_access(
    credential_name: str,
    user_or_role_name: str,
) -> None:
    """Revoke a database user or role's access to a credential.

    :param str credential_name: Name of the credential in the current schema.
    :param str user_or_role_name: Database user or role losing access.
    :return: None
    :raises: oracledb.DatabaseError
    """
    user_or_role_name = validate_user_or_role_name(user_or_role_name)
    with cursor() as cr:
        cr.execute(
            _REVOKE_CREDENTIAL_ACCESS,
            credential_name=credential_name,
            user_or_role_name=user_or_role_name,
        )


async def async_create_credential(
    credential: Mapping,
    replace: bool = False,
    public_synonym: bool = False,
):
    """Asynchronously create a credential.

    Creates a credential object using DBMS_CLOUD.CREATE_CREDENTIAL. If replace
    is True, credential will be replaced if it already exists. If
    public_synonym is True, a public synonym with the credential name is
    created for the credential in the current schema. Creating the synonym
    requires the CREATE PUBLIC SYNONYM system privilege.

    :param Mapping credential: Credential attributes accepted by
        DBMS_CLOUD.CREATE_CREDENTIAL, including credential_name.
    :param bool replace: Replace an existing credential with the same name.
    :param bool public_synonym: Create a public synonym for the credential.
    :return: None
    :raises: oracledb.DatabaseError
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

        if public_synonym:
            await cr.execute(
                _CREATE_PUBLIC_CREDENTIAL_SYNONYM,
                credential_name=credential["credential_name"],
            )


async def async_delete_credential(
    credential_name: str,
    force: bool = False,
    public_synonym: bool = False,
):
    """Asynchronously delete a credential.

    Deletes a credential object using DBMS_CLOUD.DROP_CREDENTIAL. If
    public_synonym is True, also drops its public synonym. Dropping the synonym
    requires the DROP PUBLIC SYNONYM system privilege.

    :param str credential_name: Name of the credential in the current schema.
    :param bool force: Ignore an error when the credential does not exist.
    :param bool public_synonym: Drop the credential's public synonym.
    :return: None
    :raises: oracledb.DatabaseError
    """
    async with async_cursor() as cr:
        if public_synonym:
            await cr.execute(
                _DROP_PUBLIC_CREDENTIAL_SYNONYM,
                credential_name=credential_name,
            )

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


def create_credential(
    credential: Mapping,
    replace: bool = False,
    public_synonym: bool = False,
):
    """Create a credential.

    Creates a credential object using DBMS_CLOUD.CREATE_CREDENTIAL. If replace
    is True, credential will be replaced if it "already exists". If
    public_synonym is True, a public synonym with the credential name is
    created for the credential in the current schema. Creating the synonym
    requires the CREATE PUBLIC SYNONYM system privilege.

    :param Mapping credential: Credential attributes accepted by
        DBMS_CLOUD.CREATE_CREDENTIAL, including credential_name.
    :param bool replace: Replace an existing credential with the same name.
    :param bool public_synonym: Create a public synonym for the credential.
    :return: None
    :raises: oracledb.DatabaseError
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

        if public_synonym:
            cr.execute(
                _CREATE_PUBLIC_CREDENTIAL_SYNONYM,
                credential_name=credential["credential_name"],
            )


def delete_credential(
    credential_name: str,
    force: bool = False,
    public_synonym: bool = False,
):
    """Delete a credential and optionally its public synonym.

    Dropping the synonym requires the DROP PUBLIC SYNONYM system privilege.

    :param str credential_name: Name of the credential in the current schema.
    :param bool force: Ignore an error when the credential does not exist.
    :param bool public_synonym: Drop the credential's public synonym.
    :return: None
    :raises: oracledb.DatabaseError
    """
    with cursor() as cr:
        if public_synonym:
            cr.execute(
                _DROP_PUBLIC_CREDENTIAL_SYNONYM,
                credential_name=credential_name,
            )

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
