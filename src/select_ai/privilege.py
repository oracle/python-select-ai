# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
from typing import List, Optional, Union

from .db import async_cursor, cursor
from .sql import (
    DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
    ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
    GRANT_PRIVILEGES_TO_USER,
    REVOKE_PRIVILEGES_FROM_USER,
)


def _normalize_schema_user(user: str) -> str:
    user = user.strip()
    if len(user) >= 2 and user[0] == '"' and user[-1] == '"':
        return user
    return user.upper()


def _as_list(value: Union[str, List[str]], name: str) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not value:
        raise ValueError(f"'{name}' cannot be empty")
    return value


def _append_host_ace_statement(privileges: List[str]) -> str:
    privilege_bind_names = [
        f"privilege_{idx}" for idx, _ in enumerate(privileges)
    ]
    privilege_list = ", ".join(f":{name}" for name in privilege_bind_names)
    return f"""
    BEGIN
        DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
            host => :host,
            lower_port => :lower_port,
            upper_port => :upper_port,
            ace  => xs$ace_type(
                        privilege_list => xs$name_list({privilege_list}),
                        principal_name => :user,
                        principal_type => xs_acl.ptype_db
                    )
        );
    END;
    """


def _remove_host_ace_statement(privileges: List[str]) -> str:
    privilege_bind_names = [
        f"privilege_{idx}" for idx, _ in enumerate(privileges)
    ]
    privilege_list = ", ".join(f":{name}" for name in privilege_bind_names)
    return f"""
    BEGIN
        DBMS_NETWORK_ACL_ADMIN.REMOVE_HOST_ACE(
            host => :host,
            lower_port => :lower_port,
            upper_port => :upper_port,
            ace  => xs$ace_type(
                        privilege_list => xs$name_list({privilege_list}),
                        principal_name => :user,
                        principal_type => xs_acl.ptype_db
                    )
        );
    END;
    """


def _append_host_ace_parameters(
    user: str,
    host: str,
    privileges: List[str],
    lower_port: Optional[int],
    upper_port: Optional[int],
):
    parameters = {
        "host": host,
        "user": _normalize_schema_user(user),
        "lower_port": lower_port,
        "upper_port": upper_port,
    }
    for idx, privilege in enumerate(privileges):
        parameters[f"privilege_{idx}"] = privilege
    return parameters


async def async_grant_privileges(users: Union[str, List[str]]):
    """
    This method grants execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.

    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            cr_user = _normalize_schema_user(user)
            await cr.execute(GRANT_PRIVILEGES_TO_USER, user=cr_user)


async def async_revoke_privileges(users: Union[str, List[str]]):
    """
    This method revokes execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.

    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            cr_user = _normalize_schema_user(user)
            await cr.execute(REVOKE_PRIVILEGES_FROM_USER, user=cr_user)


async def async_grant_http_access(
    users: Union[str, List[str]],
    provider_endpoint: str,
):
    """
    Async method to add ACL for HTTP access.
    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(
                ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
                user=user,
                host=provider_endpoint,
            )


async def async_grant_network_access(
    users: Union[str, List[str]],
    host: str,
    privileges: Union[str, List[str]],
    lower_port: Optional[int] = None,
    upper_port: Optional[int] = None,
):
    """
    Async method to add a network ACL entry for host access.
    """
    users = _as_list(users, "users")
    privileges = _as_list(privileges, "privileges")
    statement = _append_host_ace_statement(privileges)

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(
                statement,
                **_append_host_ace_parameters(
                    user=user,
                    host=host,
                    privileges=privileges,
                    lower_port=lower_port,
                    upper_port=upper_port,
                ),
            )


async def async_revoke_http_access(
    users: Union[str, List[str]],
    provider_endpoint: str,
):
    """
    Async method to remove ACL for HTTP access.
    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(
                DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
                user=user,
                host=provider_endpoint,
            )


async def async_revoke_network_access(
    users: Union[str, List[str]],
    host: str,
    privileges: Union[str, List[str]],
    lower_port: Optional[int] = None,
    upper_port: Optional[int] = None,
):
    """
    Async method to remove a network ACL entry for host access.
    """
    users = _as_list(users, "users")
    privileges = _as_list(privileges, "privileges")
    statement = _remove_host_ace_statement(privileges)

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(
                statement,
                **_append_host_ace_parameters(
                    user=user,
                    host=host,
                    privileges=privileges,
                    lower_port=lower_port,
                    upper_port=upper_port,
                ),
            )


def grant_privileges(users: Union[str, List[str]]):
    """
    This method grants execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr_user = _normalize_schema_user(user)
            cr.execute(GRANT_PRIVILEGES_TO_USER, user=cr_user)


def revoke_privileges(users: Union[str, List[str]]):
    """
    This method revokes execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr_user = _normalize_schema_user(user)
            cr.execute(REVOKE_PRIVILEGES_FROM_USER, user=cr_user)


def grant_http_access(users: Union[str, List[str]], provider_endpoint: str):
    """
    Adds ACL entry for HTTP access
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr.execute(
                ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
                user=user,
                host=provider_endpoint,
            )


def grant_network_access(
    users: Union[str, List[str]],
    host: str,
    privileges: Union[str, List[str]],
    lower_port: Optional[int] = None,
    upper_port: Optional[int] = None,
):
    """
    Adds a network ACL entry for host access.
    """
    users = _as_list(users, "users")
    privileges = _as_list(privileges, "privileges")
    statement = _append_host_ace_statement(privileges)

    with cursor() as cr:
        for user in users:
            cr.execute(
                statement,
                **_append_host_ace_parameters(
                    user=user,
                    host=host,
                    privileges=privileges,
                    lower_port=lower_port,
                    upper_port=upper_port,
                ),
            )


def revoke_http_access(users: Union[str, List[str]], provider_endpoint: str):
    """
    Removes ACL entry for HTTP access
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr.execute(
                DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
                user=user,
                host=provider_endpoint,
            )


def revoke_network_access(
    users: Union[str, List[str]],
    host: str,
    privileges: Union[str, List[str]],
    lower_port: Optional[int] = None,
    upper_port: Optional[int] = None,
):
    """
    Removes a network ACL entry for host access.
    """
    users = _as_list(users, "users")
    privileges = _as_list(privileges, "privileges")
    statement = _remove_host_ace_statement(privileges)

    with cursor() as cr:
        for user in users:
            cr.execute(
                statement,
                **_append_host_ace_parameters(
                    user=user,
                    host=host,
                    privileges=privileges,
                    lower_port=lower_port,
                    upper_port=upper_port,
                ),
            )
