# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import os
from threading import get_ident

import pytest

import select_ai.db as db
from select_ai.errors import DatabaseNotConnectedError

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_db_state():
    db.__conn__.clear()
    db.__async_conn__.clear()
    db.__pool__.clear()
    db.__async_pool__.clear()
    yield
    db.__conn__.clear()
    db.__async_conn__.clear()
    db.__pool__.clear()
    db.__async_pool__.clear()


def test_4200_connect_stores_thread_local_connection(monkeypatch, fake_connection):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return fake_connection

    monkeypatch.setattr(db.oracledb, "connect", fake_connect)
    db.connect(user="user", password="password", dsn="dsn")
    assert captured["connection_id_prefix"] == "python-select-ai"
    assert db.__conn__[(os.getpid(), get_ident())] is fake_connection


@pytest.mark.anyio
async def test_4201_async_connect_stores_thread_local_connection(
    monkeypatch, fake_async_connection
):
    captured = {}

    async def fake_connect_async(**kwargs):
        captured.update(kwargs)
        return fake_async_connection

    monkeypatch.setattr(db.oracledb, "connect_async", fake_connect_async)
    await db.async_connect(user="user", password="password", dsn="dsn")
    assert captured["connection_id_prefix"] == "async-python-select-ai"
    assert db.__async_conn__[(os.getpid(), get_ident())] is fake_async_connection


def test_4202_create_pool_stores_process_pool(monkeypatch, fake_pool):
    captured = {}

    def fake_create_pool(**kwargs):
        captured.update(kwargs)
        return fake_pool

    monkeypatch.setattr(db.oracledb, "create_pool", fake_create_pool)
    db.create_pool(user="user", password="password", dsn="dsn")
    assert captured["connection_id_prefix"] == "python-select-ai"
    assert db.__pool__[os.getpid()] is fake_pool


def test_4203_create_pool_async_stores_process_pool(monkeypatch, fake_async_pool):
    captured = {}

    def fake_create_pool_async(**kwargs):
        captured.update(kwargs)
        return fake_async_pool

    monkeypatch.setattr(db.oracledb, "create_pool_async", fake_create_pool_async)
    db.create_pool_async(user="user", password="password", dsn="dsn")
    assert captured["connection_id_prefix"] == "async-python-select-ai"
    assert db.__async_pool__[os.getpid()] is fake_async_pool


def test_4204_connection_manager_rejects_standalone_and_pool_together(
    fake_connection, fake_pool
):
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    db.__pool__[os.getpid()] = fake_pool
    with pytest.raises(ValueError):
        db.ConnectionManager()


def test_4205_connection_manager_yields_standalone_connection(fake_connection):
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    with db.ConnectionManager().get_connection() as connection:
        assert connection is fake_connection
    assert fake_connection.ping_count == 1


def test_4206_connection_manager_yields_pool_connection(fake_pool):
    db.__pool__[os.getpid()] = fake_pool
    with db.ConnectionManager().get_connection() as connection:
        assert connection is fake_pool.acquired_connection
    assert fake_pool.released == [fake_pool.acquired_connection]


def test_4207_connection_manager_raises_when_not_connected():
    with pytest.raises(DatabaseNotConnectedError):
        with db.ConnectionManager().get_connection():
            pass


def test_4208_is_connected_returns_true_for_healthy_connection(fake_connection):
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    assert db.is_connected() is True


def test_4209_is_connected_returns_false_for_unhealthy_connection(
    monkeypatch, fake_connection
):
    class FakeDbError(Exception):
        pass

    monkeypatch.setattr(db.oracledb, "DatabaseError", FakeDbError)
    monkeypatch.setattr(db.oracledb, "InterfaceError", FakeDbError)
    fake_connection.ping_error = FakeDbError()
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    assert db.is_connected() is False


def test_4210_cursor_closes_cursor_after_use(fake_cursor, fake_connection):
    fake_connection.cursor_factory = lambda: fake_cursor
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    with db.cursor() as cursor:
        assert cursor is fake_cursor
    assert fake_cursor.closed is True


def test_4211_disconnect_closes_standalone_connection(fake_connection):
    db.__conn__[(os.getpid(), get_ident())] = fake_connection
    db.disconnect()
    assert fake_connection.closed is True
    assert db.__conn__ == {}


def test_4212_disconnect_closes_pool(fake_pool):
    db.__pool__[os.getpid()] = fake_pool
    db.disconnect()
    assert fake_pool.closed is True
    assert fake_pool.close_force is True
    assert db.__pool__ == {}


@pytest.mark.anyio
async def test_4213_async_cursor_closes_cursor_after_use(
    fake_async_cursor, fake_async_connection
):
    fake_async_connection.cursor_factory = lambda: fake_async_cursor
    db.__async_conn__[(os.getpid(), get_ident())] = fake_async_connection
    async with db.async_cursor() as cursor:
        assert cursor is fake_async_cursor
    assert fake_async_cursor.closed is True


@pytest.mark.anyio
async def test_4214_async_is_connected_returns_true(fake_async_connection):
    db.__async_conn__[(os.getpid(), get_ident())] = fake_async_connection
    assert await db.async_is_connected() is True


@pytest.mark.anyio
async def test_4215_async_disconnect_closes_pool(fake_async_pool):
    db.__async_pool__[os.getpid()] = fake_async_pool
    await db.async_disconnect()
    assert fake_async_pool.closed is True
    assert db.__async_pool__ == {}

