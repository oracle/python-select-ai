# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
from typing import List, Union

from .db import async_cursor, cursor
from .sql import (
    DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
    ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
    GRANT_PRIVILEGES_TO_USER,
    REVOKE_PRIVILEGES_FROM_USER,
)


async def async_grant_privileges(users: Union[str, List[str]]):
    """
    This method grants execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.

    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(GRANT_PRIVILEGES_TO_USER.format(user.strip()))


async def async_revoke_privileges(users: Union[str, List[str]]):
    """
    This method revokes execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.

    """
    if isinstance(users, str):
        users = [users]

    async with async_cursor() as cr:
        for user in users:
            await cr.execute(REVOKE_PRIVILEGES_FROM_USER.format(user.strip()))


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


def grant_privileges(users: Union[str, List[str]]):
    """
    This method grants execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr.execute(GRANT_PRIVILEGES_TO_USER.format(user.strip()))


def revoke_privileges(users: Union[str, List[str]]):
    """
    This method revokes execute privilege on the packages DBMS_CLOUD,
    DBMS_CLOUD_AI, DBMS_CLOUD_AI_AGENT and DBMS_CLOUD_PIPELINE.
    """
    if isinstance(users, str):
        users = [users]
    with cursor() as cr:
        for user in users:
            cr.execute(REVOKE_PRIVILEGES_FROM_USER.format(user.strip()))


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
