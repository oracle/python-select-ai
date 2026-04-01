# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
from unittest.mock import AsyncMock, Mock

import pytest

import select_ai.credential as credential

pytestmark = pytest.mark.unit


@contextlib.contextmanager
def _cursor_manager(cursor):
    yield cursor


@contextlib.asynccontextmanager
async def _async_cursor_manager(cursor):
    yield cursor


def test_4300_validate_credential_accepts_supported_keys():
    credential._validate_credential(
        {
            "credential_name": "cred",
            "username": "user",
            "password": "secret",
            "comments": "demo",
        }
    )


def test_4301_validate_credential_rejects_invalid_keys():
    with pytest.raises(ValueError):
        credential._validate_credential({"credential_name": "cred", "token": "x"})


def test_4302_create_credential_calls_dbms_cloud_create(monkeypatch):
    callproc = Mock()
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "cursor", lambda: _cursor_manager(fake_cursor)
    )
    credential.create_credential({"credential_name": "cred", "username": "openai"})
    callproc.assert_called_once_with(
        "DBMS_CLOUD.CREATE_CREDENTIAL",
        keyword_parameters={"credential_name": "cred", "username": "openai"},
    )


def test_4303_create_credential_replaces_on_duplicate(monkeypatch, error_factory):
    callproc = Mock(side_effect=[error_factory(20022), None, None])
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "cursor", lambda: _cursor_manager(fake_cursor)
    )
    monkeypatch.setattr(credential.oracledb, "DatabaseError", type(error_factory(1)))
    payload = {"credential_name": "cred", "username": "openai"}
    credential.create_credential(payload, replace=True)
    assert callproc.call_count == 3


def test_4304_create_credential_reraises_unknown_errors(monkeypatch, error_factory):
    fake_error = type(error_factory(1))
    callproc = Mock(side_effect=error_factory(20999))
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "cursor", lambda: _cursor_manager(fake_cursor)
    )
    monkeypatch.setattr(credential.oracledb, "DatabaseError", fake_error)
    with pytest.raises(fake_error):
        credential.create_credential({"credential_name": "cred"})


def test_4305_delete_credential_ignores_missing_when_forced(
    monkeypatch, error_factory
):
    fake_error = type(error_factory(1))
    callproc = Mock(side_effect=error_factory(20004))
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "cursor", lambda: _cursor_manager(fake_cursor)
    )
    monkeypatch.setattr(credential.oracledb, "DatabaseError", fake_error)
    credential.delete_credential("cred", force=True)


@pytest.mark.anyio
async def test_4306_async_create_credential_replaces_on_duplicate(
    monkeypatch, error_factory
):
    fake_error = type(error_factory(1))
    callproc = AsyncMock(side_effect=[error_factory(20022), None, None])
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "async_cursor", lambda: _async_cursor_manager(fake_cursor)
    )
    monkeypatch.setattr(credential.oracledb, "DatabaseError", fake_error)
    payload = {"credential_name": "cred", "username": "openai"}
    await credential.async_create_credential(payload, replace=True)
    assert callproc.await_count == 3


@pytest.mark.anyio
async def test_4307_async_delete_credential_ignores_missing_when_forced(
    monkeypatch, error_factory
):
    fake_error = type(error_factory(1))
    callproc = AsyncMock(side_effect=error_factory(20004))
    fake_cursor = Mock(callproc=callproc)
    monkeypatch.setattr(
        credential, "async_cursor", lambda: _async_cursor_manager(fake_cursor)
    )
    monkeypatch.setattr(credential.oracledb, "DatabaseError", fake_error)
    await credential.async_delete_credential("cred", force=True)
