# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
import os
from threading import get_ident
from typing import Any, AsyncGenerator, Dict, Generator, Hashable, Optional

import oracledb
from oracledb import Connection

from select_ai.errors import DatabaseNotConnectedError

__conn__: Dict[Hashable, oracledb.Connection] = {}
__async_conn__: Dict[Hashable, oracledb.AsyncConnection] = {}

__pool__: Dict[Hashable, oracledb.ConnectionPool] = {}
__async_pool__: Dict[Hashable, oracledb.AsyncConnectionPool] = {}

__all__ = [
    "connect",
    "create_pool",
    "create_pool_async",
    "async_connect",
    "is_connected",
    "async_is_connected",
    "get_connection",
    "async_get_connection",
    "cursor",
    "async_cursor",
    "disconnect",
    "async_disconnect",
]


def connect(user: str, password: str, dsn: str, *args, **kwargs):
    """Creates an oracledb.Connection object
    and saves it global dictionary __conn__
    The connection object is thread local meaning
    in a multithreaded application, individual
    threads cannot see each other's connection
    object
    """
    conn = oracledb.connect(
        user=user,
        password=password,
        dsn=dsn,
        connection_id_prefix="python-select-ai",
        *args,
        **kwargs,
    )
    _set_connection(conn=conn)


def create_pool(
    user: str,
    password: str,
    dsn: str,
    min_size: Optional[int] = 1,
    max_size: Optional[int] = 2,
    increment: Optional[int] = 1,
    *args,
    **kwargs,
):
    pool = oracledb.create_pool(
        user=user,
        password=password,
        dsn=dsn,
        min=min_size,
        max=max_size,
        increment=increment,
        connection_id_prefix="python-select-ai",
        getmode=oracledb.POOL_GETMODE_NOWAIT,
        *args,
        **kwargs,
    )
    _set_connection_pool(pool=pool)


def create_pool_async(
    user: str,
    password: str,
    dsn: str,
    min_size: Optional[int] = 1,
    max_size: Optional[int] = 1,
    increment: Optional[int] = 1,
    *args,
    **kwargs,
):
    async_pool = oracledb.create_pool_async(
        user=user,
        password=password,
        dsn=dsn,
        min=min_size,
        max=max_size,
        increment=increment,
        connection_id_prefix="async-python-select-ai",
        *args,
        **kwargs,
    )
    _set_connection_pool(async_pool=async_pool)


async def async_connect(user: str, password: str, dsn: str, *args, **kwargs):
    """Creates an oracledb.AsyncConnection object
    and saves it global dictionary __async_conn__
    The connection object is thread local meaning
    in a multithreaded application, individual
    threads cannot see each other's connection
    object
    """
    async_conn = await oracledb.connect_async(
        user=user,
        password=password,
        dsn=dsn,
        connection_id_prefix="async-python-select-ai",
        *args,
        **kwargs,
    )
    _set_connection(async_conn=async_conn)


def is_connected() -> bool:
    """Checks if database connection is open and healthy"""
    global __conn__
    key = (os.getpid(), get_ident())
    conn = __conn__.get(key)
    if conn is None:
        return False
    try:
        return conn.ping() is None
    except (oracledb.DatabaseError, oracledb.InterfaceError):
        return False


async def async_is_connected() -> bool:
    """Asynchronously checks if database connection is open and healthy"""

    global __async_conn__
    key = (os.getpid(), get_ident())
    conn = __async_conn__.get(key)
    if conn is None:
        return False
    try:
        return await conn.ping() is None
    except (oracledb.DatabaseError, oracledb.InterfaceError):
        return False


def _set_connection(
    conn: oracledb.Connection = None,
    async_conn: oracledb.AsyncConnection = None,
):
    """Set existing connection for select_ai Python API to reuse

    :param conn: python-oracledb Connection object
    :param async_conn: python-oracledb
    :return:
    """
    key = (os.getpid(), get_ident())
    if conn:
        global __conn__
        __conn__[key] = conn
    if async_conn:
        global __async_conn__
        __async_conn__[key] = async_conn


def _set_connection_pool(
    pool: Optional[oracledb.ConnectionPool] = None,
    async_pool: Optional[oracledb.AsyncConnectionPool] = None,
):
    """Set existing connection pool for select_ai Python API to reuse

    :param pool: python-oracledb ConnectionPool object
    :param async_pool: python-oracledb AsyncConnectionPool object

    :return: None
    """
    key = (os.getpid(), get_ident())
    if pool:
        global __pool__
        __pool__[key] = pool
    if async_pool:
        global __async_pool__
        __async_pool__[key] = async_pool


@contextlib.contextmanager
def get_connection() -> Generator[Connection, Any, None]:
    """Returns the connection object if connection is healthy"""
    with ConnectionManager().get_connection() as conn:
        yield conn


@contextlib.asynccontextmanager
async def async_get_connection() -> AsyncGenerator[Any, Any]:
    """Returns the AsyncConnection object if connection is healthy"""
    async with ConnectionManager().get_connection() as conn:
        yield conn


@contextlib.contextmanager
def cursor():
    """
    Creates a context manager for database cursor

    Typical usage:

        with select_ai.cursor() as cr:
            cr.execute(<QUERY>)

    This ensures that the cursor is closed regardless
    of whether an exception occurred

    """
    with ConnectionManager().get_connection() as conn:
        cr = conn.cursor()
        try:
            yield cr
        finally:
            cr.close()


@contextlib.asynccontextmanager
async def async_cursor():
    """
    Creates an async context manager for database cursor

    Typical usage:

        async with select_ai.cursor() as cr:
            await cr.execute(<QUERY>)
    :return:
    """
    async with AsyncConnectionManager().get_connection() as conn:
        cr = conn.cursor()
        try:
            yield cr
        finally:
            cr.close()


def disconnect():
    connection_manager = ConnectionManager()
    connection_manager.disconnect()


async def async_disconnect():
    connection_manager = AsyncConnectionManager()
    await connection_manager.disconnect()


class ConnectionManager:
    """
    Manages standalone connections and connection pools
    """

    def __init__(self):
        global __conn__, __pool__
        self.key = (os.getpid(), get_ident())
        self.conn = __conn__.get(self.key)
        self.pool = __pool__.get(self.key)
        if self.conn and self.pool:
            raise ValueError(
                "Use either a standalone connection " "or a connection pool"
            )

    @property
    def is_standalone(self):
        return self.conn is not None

    @property
    def is_pool(self):
        return self.pool is not None

    @contextlib.contextmanager
    def get_connection(self) -> Generator[Connection, Any, None]:
        if self.is_pool:
            with self.connection_from_pool() as conn:
                yield conn
        else:
            with self.standalone_connection() as conn:
                yield conn

    @contextlib.contextmanager
    def connection_from_pool(self) -> Generator[Connection, Any, None]:
        if self.is_pool:
            try:
                conn = self.pool.acquire()
            except (oracledb.DatabaseError, oracledb.InterfaceError):
                raise DatabaseNotConnectedError()
        else:
            raise DatabaseNotConnectedError()
        try:
            yield conn
        finally:
            self.pool.release(conn)

    @contextlib.contextmanager
    def standalone_connection(self) -> Generator[Connection, Any, None]:
        if self.is_standalone:
            try:
                self.conn.ping()
            except (oracledb.DatabaseError, oracledb.InterfaceError):
                raise DatabaseNotConnectedError()
            yield self.conn
        else:
            raise DatabaseNotConnectedError()

    def disconnect(self, force=True):
        global __pool__, __conn__
        if self.is_pool:
            self.pool.close(force=force)
            __pool__.pop(self.key, None)
        elif self.is_standalone:
            self.conn.close()
            __conn__.pop(self.key, None)


class AsyncConnectionManager:
    """
    Manages async standalone connections and connection pools
    """

    def __init__(self):
        global __async_conn__, __async_pool__
        self.key = (os.getpid(), get_ident())
        self.conn = __async_conn__.get(self.key)
        self.pool = __async_pool__.get(self.key)
        if self.conn and self.pool:
            raise ValueError(
                "Use either a standalone connection " "or a connection pool"
            )

    @property
    def is_standalone(self):
        return self.conn is not None

    @property
    def is_pool(self):
        return self.pool is not None

    @contextlib.asynccontextmanager
    async def get_connection(self):
        if self.is_pool:
            async with self.connection_from_pool() as conn:
                yield conn
        else:
            async with self.standalone_connection() as conn:
                yield conn

    @contextlib.asynccontextmanager
    async def connection_from_pool(self):
        if self.is_pool:
            try:
                conn = await self.pool.acquire()
            except (oracledb.DatabaseError, oracledb.InterfaceError):
                raise DatabaseNotConnectedError()
        else:
            raise DatabaseNotConnectedError()
        try:
            yield conn
        finally:
            await self.pool.release(conn)

    @contextlib.asynccontextmanager
    async def standalone_connection(self):
        if self.is_standalone:
            try:
                await self.conn.ping()
            except (oracledb.DatabaseError, oracledb.InterfaceError):
                raise DatabaseNotConnectedError()
            yield self.conn
        else:
            raise DatabaseNotConnectedError()

    async def disconnect(self, force=False):
        global __async_conn__, __async_pool__
        if self.is_pool:
            await self.pool.close(force=force)
            __async_pool__.pop(self.key, None)
        elif self.is_standalone:
            await self.conn.close()
            __async_conn__.pop(self.key, None)
