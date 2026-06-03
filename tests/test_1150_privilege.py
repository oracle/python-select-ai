# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1150 - Privilege API tests
"""

import uuid

import pytest
import select_ai


def _network_ace_exists(cursor, host, principal, privilege, lower_port=None):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM DBA_HOST_ACES
        WHERE host = :host
        AND principal = :principal
        AND privilege = :privilege
        AND (lower_port = :lower_port OR (lower_port IS NULL AND :lower_port IS NULL))
        """,
        host=host,
        principal=principal,
        privilege=privilege,
        lower_port=lower_port,
    )
    return cursor.fetchone()[0] > 0


@pytest.fixture
def admin_connect(test_env):
    select_ai.disconnect()
    select_ai.create_pool(**test_env.connect_params(admin=True, use_pool=True))
    yield
    select_ai.disconnect()
    select_ai.create_pool(**test_env.connect_params(use_pool=True))


@pytest.fixture
async def async_admin_connect(test_env):
    await select_ai.async_disconnect()
    select_ai.create_pool_async(
        **test_env.connect_params(admin=True, use_pool=True)
    )
    yield
    await select_ai.async_disconnect()
    select_ai.create_pool_async(**test_env.connect_params(use_pool=True))


def test_1150_grant_network_access(admin_connect, test_env):
    host = f"pysai-{uuid.uuid4().hex}.example.com"
    principal = test_env.test_user.upper()

    select_ai.grant_network_access(
        users=test_env.test_user,
        host=host,
        privileges=["connect", "smtp"],
        lower_port=587,
        upper_port=587,
    )

    with select_ai.cursor() as cursor:
        assert _network_ace_exists(cursor, host, principal, "CONNECT", 587)
        assert _network_ace_exists(cursor, host, principal, "SMTP", 587)


@pytest.mark.anyio
async def test_1151_async_grant_network_access(async_admin_connect, test_env):
    host = f"pysai-{uuid.uuid4().hex}.example.com"
    principal = test_env.test_user.upper()

    await select_ai.async_grant_network_access(
        users=test_env.test_user,
        host=host,
        privileges="connect",
    )

    async with select_ai.async_cursor() as cursor:
        await cursor.execute(
            """
            SELECT COUNT(*)
            FROM DBA_HOST_ACES
            WHERE host = :host
            AND principal = :principal
            AND privilege = 'CONNECT'
            """,
            host=host,
            principal=principal,
        )
        count = await cursor.fetchone()
        assert count[0] > 0
