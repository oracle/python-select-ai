# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import contextlib
import os
from threading import get_ident
from typing import Dict, Hashable

import oracledb

from select_ai.errors import DatabaseNotConnectedError

__conn__: Dict[Hashable, oracledb.Connection] = {}
__async_conn__: Dict[Hashable, oracledb.AsyncConnection] = {}

__all__ = [
    "connect",
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


def get_connection() -> oracledb.Connection:
    """Returns the connection object if connection is healthy"""
    if not is_connected():
        raise DatabaseNotConnectedError()
    global __conn__
    key = (os.getpid(), get_ident())
    return __conn__[key]


async def async_get_connection() -> oracledb.AsyncConnection:
    """Returns the AsyncConnection object if connection is healthy"""
    if not await async_is_connected():
        raise DatabaseNotConnectedError()
    global __async_conn__
    key = (os.getpid(), get_ident())
    return __async_conn__[key]


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
    cr = get_connection().cursor()
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
    conn = await async_get_connection()
    cr = conn.cursor()
    try:
        yield cr
    finally:
        cr.close()


def disconnect():
    try:
        conn = get_connection()
    except DatabaseNotConnectedError:
        pass
    else:
        conn.close()


async def async_disconnect():
    try:
        conn = await async_get_connection()
    except DatabaseNotConnectedError:
        pass
    else:
        await conn.close()
