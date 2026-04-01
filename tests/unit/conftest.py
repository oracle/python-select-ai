# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True, scope="session")
def setup_test_user():
    yield


@pytest.fixture(autouse=True, scope="module")
def connect():
    yield


@pytest.fixture(autouse=True, scope="module")
def async_connect():
    yield


@pytest.fixture(autouse=True, scope="module")
def oci_credential():
    yield {}


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


class FakeCursor:

    def __init__(self):
        self.execute_calls = []
        self.callproc_calls = []
        self.callfunc_calls = []
        self.fetchone_result = None
        self.fetchall_result = []
        self.closed = False

    def execute(self, statement, *args, **kwargs):
        self.execute_calls.append((statement, args, kwargs))
        return None

    def callproc(self, name, *args, **kwargs):
        self.callproc_calls.append((name, args, kwargs))
        return None

    def callfunc(self, name, return_type, *args, **kwargs):
        self.callfunc_calls.append((name, return_type, args, kwargs))
        return None

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result

    def close(self):
        self.closed = True


class FakeAsyncCursor:

    def __init__(self):
        self.execute_calls = []
        self.callproc_calls = []
        self.callfunc_calls = []
        self.fetchone_result = None
        self.fetchall_result = []
        self.closed = False

    async def execute(self, statement, *args, **kwargs):
        self.execute_calls.append((statement, args, kwargs))
        return None

    async def callproc(self, name, *args, **kwargs):
        self.callproc_calls.append((name, args, kwargs))
        return None

    async def callfunc(self, name, return_type, *args, **kwargs):
        self.callfunc_calls.append((name, return_type, args, kwargs))
        return None

    async def fetchone(self):
        return self.fetchone_result

    async def fetchall(self):
        return self.fetchall_result

    def close(self):
        self.closed = True


class FakeConnection:

    def __init__(self, cursor_factory=None, ping_error=None):
        self.cursor_factory = cursor_factory or FakeCursor
        self.ping_error = ping_error
        self.closed = False
        self.ping_count = 0

    def ping(self):
        self.ping_count += 1
        if self.ping_error is not None:
            raise self.ping_error

    def cursor(self):
        return self.cursor_factory()

    def close(self):
        self.closed = True


class FakeAsyncConnection:

    def __init__(self, cursor_factory=None, ping_error=None):
        self.cursor_factory = cursor_factory or FakeAsyncCursor
        self.ping_error = ping_error
        self.closed = False
        self.ping_count = 0

    async def ping(self):
        self.ping_count += 1
        if self.ping_error is not None:
            raise self.ping_error

    def cursor(self):
        return self.cursor_factory()

    async def close(self):
        self.closed = True


class FakePool:

    def __init__(self, acquired_connection=None, acquire_error=None):
        self.acquired_connection = acquired_connection or FakeConnection()
        self.acquire_error = acquire_error
        self.released = []
        self.closed = False
        self.close_force = None

    def acquire(self):
        if self.acquire_error is not None:
            raise self.acquire_error
        return self.acquired_connection

    def release(self, connection):
        self.released.append(connection)

    def close(self, force=False):
        self.closed = True
        self.close_force = force


class FakeAsyncPool:

    def __init__(self, acquired_connection=None, acquire_error=None):
        self.acquired_connection = acquired_connection or FakeAsyncConnection()
        self.acquire_error = acquire_error
        self.released = []
        self.closed = False
        self.close_force = None

    async def acquire(self):
        if self.acquire_error is not None:
            raise self.acquire_error
        return self.acquired_connection

    async def release(self, connection):
        self.released.append(connection)

    async def close(self, force=False):
        self.closed = True
        self.close_force = force


class FakeLOB:

    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


class FakeAsyncLOB:

    def __init__(self, value):
        self.value = value

    async def read(self):
        return self.value


class FakeDatabaseError(Exception):

    def __init__(self, code):
        super().__init__(code)
        self.args = (SimpleNamespace(code=code),)


@contextlib.contextmanager
def sync_cursor_manager(cursor):
    yield cursor


@contextlib.asynccontextmanager
async def async_cursor_manager(cursor):
    yield cursor


@pytest.fixture
def error_factory():
    def _factory(code):
        return FakeDatabaseError(code)

    return _factory


@pytest.fixture
def fake_cursor():
    return FakeCursor()


@pytest.fixture
def fake_async_cursor():
    return FakeAsyncCursor()


@pytest.fixture
def fake_connection():
    return FakeConnection()


@pytest.fixture
def fake_async_connection():
    return FakeAsyncConnection()


@pytest.fixture
def fake_pool():
    return FakePool()


@pytest.fixture
def fake_async_pool():
    return FakeAsyncPool()


@pytest.fixture
def fake_lob():
    return FakeLOB("lob-value")


@pytest.fixture
def fake_async_lob():
    return FakeAsyncLOB("async-lob-value")
