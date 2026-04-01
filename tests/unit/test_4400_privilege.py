# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
from unittest.mock import AsyncMock, Mock

import pytest

import select_ai.privilege as privilege

pytestmark = pytest.mark.unit


@contextlib.contextmanager
def _cursor_manager(cursor):
    yield cursor


@contextlib.asynccontextmanager
async def _async_cursor_manager(cursor):
    yield cursor


def test_4400_grant_privileges_normalizes_single_user(monkeypatch):
    fake_cursor = Mock(execute=Mock())
    monkeypatch.setattr(privilege, "cursor", lambda: _cursor_manager(fake_cursor))
    privilege.grant_privileges("  DEMO_USER  ")
    fake_cursor.execute.assert_called_once()
    statement = fake_cursor.execute.call_args.args[0]
    assert "DEMO_USER" in statement


def test_4401_revoke_privileges_accepts_multiple_users(monkeypatch):
    fake_cursor = Mock(execute=Mock())
    monkeypatch.setattr(privilege, "cursor", lambda: _cursor_manager(fake_cursor))
    privilege.revoke_privileges(["USER_ONE", "USER_TWO"])
    assert fake_cursor.execute.call_count == 2


def test_4402_grant_http_access_passes_host_parameter(monkeypatch):
    fake_cursor = Mock(execute=Mock())
    monkeypatch.setattr(privilege, "cursor", lambda: _cursor_manager(fake_cursor))
    privilege.grant_http_access(["USER_ONE", "USER_TWO"], "api.openai.com")
    assert fake_cursor.execute.call_count == 2
    _, kwargs = fake_cursor.execute.call_args
    assert kwargs == {"user": "USER_TWO", "host": "api.openai.com"}


def test_4403_revoke_http_access_passes_host_parameter(monkeypatch):
    fake_cursor = Mock(execute=Mock())
    monkeypatch.setattr(privilege, "cursor", lambda: _cursor_manager(fake_cursor))
    privilege.revoke_http_access("USER_ONE", "api.openai.com")
    fake_cursor.execute.assert_called_once_with(
        privilege.DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
        user="USER_ONE",
        host="api.openai.com",
    )


@pytest.mark.anyio
async def test_4404_async_grant_privileges_normalizes_single_user(monkeypatch):
    fake_cursor = Mock(execute=AsyncMock())
    monkeypatch.setattr(
        privilege, "async_cursor", lambda: _async_cursor_manager(fake_cursor)
    )
    await privilege.async_grant_privileges("  DEMO_USER  ")
    statement = fake_cursor.execute.call_args.args[0]
    assert "DEMO_USER" in statement


@pytest.mark.anyio
async def test_4405_async_http_access_helpers_use_expected_parameters(monkeypatch):
    fake_cursor = Mock(execute=AsyncMock())
    monkeypatch.setattr(
        privilege, "async_cursor", lambda: _async_cursor_manager(fake_cursor)
    )
    await privilege.async_grant_http_access("USER_ONE", "api.openai.com")
    fake_cursor.execute.assert_awaited_once_with(
        privilege.ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
        user="USER_ONE",
        host="api.openai.com",
    )
