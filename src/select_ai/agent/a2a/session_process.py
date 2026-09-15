# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Reusable child-process backend for isolated database sessions."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import multiprocessing
import time
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Protocol

from select_ai.agent.a2a.session_runtime import SessionRuntime
from select_ai.agent.a2a.worker_protocol import (
    PipeMessageType,
    ResultKind,
    WorkerResult,
)

LOGGER = logging.getLogger(__name__)
_SESSION_REAPER_INTERVAL_SECONDS = 1


@dataclass(frozen=True)
class SessionSpec:
    """Complete inputs needed to start one isolated session."""

    session_id: str
    dsn: str
    username: str
    password: str
    team_name: str


@dataclass
class ChildSession:
    """In-memory ownership record for one database-session process."""

    process: multiprocessing.Process
    connection: Connection
    expires_at: float
    lock: asyncio.Lock


class SessionBackend(Protocol):
    """Internal contract shared by worker and embedded session backends."""

    async def open(self, spec: SessionSpec) -> None: ...

    async def dispatch(
        self,
        session_id: str,
        method: str,
        payload: bytes,
    ) -> WorkerResult: ...

    async def close(self, session_id: str) -> None: ...

    async def close_all(self) -> None: ...

    async def reap_expired(self) -> None: ...


class SessionBackendError(RuntimeError):
    """Base error raised by an isolated session backend."""


class SessionNotFound(SessionBackendError):
    """The requested session does not exist or is no longer live."""


class SessionUnavailable(SessionBackendError):
    """The session process failed while handling a command."""


class SessionStartTimeout(SessionBackendError):
    """The session process did not become ready before its deadline."""


class SessionLoginError(SessionBackendError):
    """The database connection or team initialization failed."""


class SessionCommandError(SessionBackendError):
    """The database runtime rejected one A2A command."""


class ProcessSessionBackend:
    """Own one isolated Select AI runtime process for each session."""

    def __init__(
        self,
        session_ttl_seconds: int,
        session_start_timeout_seconds: int,
    ) -> None:
        self.session_ttl_seconds = session_ttl_seconds
        self.session_start_timeout_seconds = session_start_timeout_seconds
        self.sessions: dict[str, ChildSession] = {}

    async def open(self, spec: SessionSpec) -> None:
        """Start a child runtime and wait until its database pool is ready."""
        parent_connection, child_connection = multiprocessing.Pipe()
        credentials = {
            "user": spec.username,
            "password": spec.password,
            "dsn": spec.dsn,
        }
        process = multiprocessing.Process(
            target=_session_process_main,
            args=(
                child_connection,
                credentials,
                spec.session_id,
                spec.team_name,
            ),
            daemon=True,
        )
        process.start()
        child_connection.close()
        session = ChildSession(
            process=process,
            connection=parent_connection,
            expires_at=time.monotonic() + self.session_ttl_seconds,
            lock=asyncio.Lock(),
        )
        try:
            await self._wait_ready(session, spec)
        except Exception:
            await self._terminate(session)
            raise
        previous = self.sessions.pop(spec.session_id, None)
        self.sessions[spec.session_id] = session
        if previous:
            await self._terminate(previous)

    async def get(self, session_id: str) -> ChildSession:
        """Return a live session, closing it if its expiry has elapsed."""
        expired_session = None
        session = self.sessions.get(session_id)
        if session and (
            session.expires_at <= time.monotonic()
            or not session.process.is_alive()
        ):
            self.sessions.pop(session_id, None)
            expired_session = session
            session = None
        if expired_session:
            await self._terminate(expired_session)
        if session is None:
            raise SessionNotFound(
                "Database session expired; reconnect required."
            )
        return session

    async def dispatch(
        self,
        session_id: str,
        method: str,
        payload: bytes,
    ) -> WorkerResult:
        """Run one A2A operation in the process owning this session."""
        session = await self.get(session_id)
        response = None
        failure = None
        async with session.lock:
            if session.process.is_alive():
                try:
                    await asyncio.to_thread(
                        session.connection.send,
                        {
                            "type": PipeMessageType.A2A.value,
                            "method": method,
                            "payload": payload,
                        },
                    )
                    response = await self._receive(
                        session,
                        timeout_seconds=120,
                    )
                except (EOFError, OSError, TimeoutError) as error:
                    failure = error
        if failure is not None:
            await self._discard(session_id, session)
            raise SessionUnavailable(
                "Database session is unavailable; reconnect required."
            ) from failure
        if response is None:
            await self._discard(session_id, session)
            raise SessionNotFound(
                "Database session expired; reconnect required."
            )
        if response.get("type") == PipeMessageType.RESULT.value:
            return response.get(
                "result",
                WorkerResult(ResultKind.NONE),
            )
        if response.get("type") == PipeMessageType.A2A_ERROR.value:
            raise SessionCommandError(
                response.get("detail", "A2A request failed.")
            )
        LOGGER.error("Select AI session process reported a command failure.")
        raise SessionUnavailable(
            "Database session is unavailable; reconnect required."
        )

    async def close(self, session_id: str) -> None:
        """Terminate a session explicitly."""
        session = self.sessions.pop(session_id, None)
        if session is None:
            raise SessionNotFound(
                "Database session expired; reconnect required."
            )
        await self._terminate(session)

    async def reap_expired(self) -> None:
        """Continuously terminate expired or dead child sessions."""
        while True:
            await asyncio.sleep(_SESSION_REAPER_INTERVAL_SECONDS)
            await self._reap_expired_sessions()

    async def close_all(self) -> None:
        """Terminate all child sessions during backend shutdown."""
        sessions = list(self.sessions.values())
        self.sessions.clear()
        for session in sessions:
            await self._terminate(session)

    async def _reap_expired_sessions(self) -> None:
        now = time.monotonic()
        expired = [
            (session_id, session)
            for session_id, session in self.sessions.items()
            if session.expires_at <= now or not session.process.is_alive()
        ]
        for session_id, _session in expired:
            self.sessions.pop(session_id, None)

        for session_id, session in expired:
            try:
                await self._terminate(session)
            except Exception:
                LOGGER.exception(
                    "Failed to terminate expired session %s.",
                    session_id,
                )

    async def _wait_ready(
        self,
        session: ChildSession,
        spec: SessionSpec,
    ) -> None:
        try:
            response = await self._receive(
                session,
                timeout_seconds=self.session_start_timeout_seconds,
            )
        except (EOFError, OSError, TimeoutError) as error:
            raise SessionStartTimeout(
                "Database session start timed out."
            ) from error
        if response.get("type") == PipeMessageType.READY.value:
            return
        detail = response.get("detail", "Database login failed.")
        for secret in (spec.password, spec.username, spec.dsn):
            detail = detail.replace(secret, "[REDACTED]")
        LOGGER.error("Select AI session startup failed: %s", detail[-2_000:])
        raise SessionLoginError("Database login failed.")

    @staticmethod
    async def _receive(
        session: ChildSession,
        timeout_seconds: float,
    ) -> dict:
        available = await asyncio.to_thread(
            session.connection.poll,
            timeout_seconds,
        )
        if not available:
            raise TimeoutError()
        return await asyncio.to_thread(session.connection.recv)

    async def _discard(self, session_id: str, session: ChildSession) -> None:
        if self.sessions.get(session_id) is session:
            self.sessions.pop(session_id, None)
        await self._terminate(session)

    @staticmethod
    async def _terminate(session: ChildSession) -> None:
        async with session.lock:
            try:
                with contextlib.suppress(OSError):
                    await asyncio.to_thread(
                        session.connection.send,
                        {"type": PipeMessageType.CLOSE.value},
                    )
                await asyncio.to_thread(session.process.join, timeout=5)
                for stop in (
                    session.process.terminate,
                    session.process.kill,
                ):
                    if not session.process.is_alive():
                        break
                    await asyncio.to_thread(stop)
                    await asyncio.to_thread(session.process.join, timeout=5)
            finally:
                await asyncio.to_thread(session.connection.close)


def _session_process_main(
    connection: Connection,
    credentials: dict[str, str],
    session_id: str,
    team_name: str,
) -> None:
    """Entrypoint for a child that owns one Select AI database session."""
    try:
        asyncio.run(
            _run_session_process(
                connection,
                credentials,
                session_id,
                team_name,
            )
        )
    finally:
        connection.close()


async def _run_session_process(
    connection: Connection,
    credentials: dict[str, str],
    session_id: str,
    team_name: str,
) -> None:
    """Open one async connection and execute A2A operations."""
    import select_ai

    runtime: SessionRuntime | None = None
    ready = False
    try:
        await select_ai.async_connect(
            user=credentials["user"],
            password=credentials["password"],
            dsn=credentials["dsn"],
        )
        if not await select_ai.async_is_connected():
            raise RuntimeError("Database login failed.")
        runtime = SessionRuntime(session_id, team_name)
        await runtime.initialize()
        connection.send({"type": PipeMessageType.READY.value})
        ready = True
        await _serve_session_commands(connection, runtime)
    except Exception as error:
        _report_session_process_error(connection, error, not ready)
    finally:
        await _close_session_process(runtime, select_ai)


async def _serve_session_commands(
    connection: Connection,
    runtime: SessionRuntime,
) -> None:
    """Serve commands for one initialized database session."""
    while True:
        command = await _receive_session_command(connection)
        if (
            command is None
            or command.get("type") == PipeMessageType.CLOSE.value
        ):
            return
        if command.get("type") != PipeMessageType.A2A.value:
            connection.send(
                {
                    "type": PipeMessageType.ERROR.value,
                    "detail": "Invalid command.",
                }
            )
            continue
        await _handle_a2a_command(connection, runtime, command)


async def _receive_session_command(connection: Connection) -> dict | None:
    """Read one command without blocking the event loop."""
    try:
        return await asyncio.to_thread(connection.recv)
    except EOFError:
        return None


async def _handle_a2a_command(
    connection: Connection,
    runtime: SessionRuntime,
    command: dict,
) -> None:
    """Execute one internal A2A command and send its result."""
    try:
        result = await runtime.handle(
            command["method"],
            command.get("payload", b""),
        )
    except Exception as error:
        LOGGER.exception("Select AI session A2A command failed")
        connection.send(
            {"type": PipeMessageType.A2A_ERROR.value, "detail": str(error)}
        )
        return
    connection.send({"type": PipeMessageType.RESULT.value, "result": result})


def _report_session_process_error(
    connection: Connection,
    error: Exception,
    during_startup: bool,
) -> None:
    """Report startup failures without sending errors after readiness."""
    message = (
        "Select AI session process startup failed"
        if during_startup
        else "Select AI session process failed"
    )
    LOGGER.error(message)
    if during_startup:
        with contextlib.suppress(OSError):
            connection.send(
                {"type": PipeMessageType.ERROR.value, "detail": str(error)}
            )


async def _close_session_process(
    runtime: SessionRuntime | None,
    select_ai,
) -> None:
    """Close the A2A handler and database connection owned by the child."""
    handler = getattr(runtime, "handler", None)
    if handler is not None:
        with contextlib.suppress(Exception):
            await handler.aclose()
    with contextlib.suppress(Exception):
        await select_ai.async_disconnect()
