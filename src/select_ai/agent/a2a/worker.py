# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Internal worker that owns temporary Select AI child processes."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import multiprocessing
import os
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field, SecretStr
from starlette.responses import Response

from select_ai.agent.a2a.session_runtime import SessionRuntime
from select_ai.agent.a2a.worker_protocol import (
    PROTOBUF_CONTENT_TYPE,
    WORKER_A2A_METHOD_HEADER,
    WORKER_RESULT_KIND_HEADER,
    PipeMessageType,
    ResultKind,
    WorkerResult,
)

LOGGER = logging.getLogger(__name__)
_SESSION_REAPER_INTERVAL_SECONDS = 1


class OpenSessionRequest(BaseModel):
    """Sensitive request accepted only on the internal worker interface."""

    session_id: str
    dsn: str = Field(min_length=1, max_length=4_000)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=1_024)
    team_name: str = Field(min_length=1, max_length=128)


@dataclass
class ChildSession:
    """In-memory ownership record for one database-session process."""

    process: multiprocessing.Process
    connection: Connection
    expires_at: float
    lock: asyncio.Lock


class SessionWorker:
    """Own one isolated Select AI runtime process for each session."""

    def __init__(
        self,
        session_ttl_seconds: int,
        session_start_timeout_seconds: int,
    ) -> None:
        self.session_ttl_seconds = session_ttl_seconds
        self.session_start_timeout_seconds = session_start_timeout_seconds
        self.sessions: dict[str, ChildSession] = {}

    async def open(self, request: OpenSessionRequest) -> None:
        """Start a child runtime and wait until its database pool is ready."""
        parent_connection, child_connection = multiprocessing.Pipe()
        credentials = {
            "user": request.username,
            "password": request.password.get_secret_value(),
            "dsn": request.dsn,
        }
        process = multiprocessing.Process(
            target=_session_process_main,
            args=(
                child_connection,
                credentials,
                request.session_id,
                request.team_name,
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
            await self._wait_ready(session, request)
        except Exception:
            await self._terminate(session)
            raise
        previous = self.sessions.pop(request.session_id, None)
        self.sessions[request.session_id] = session
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
            raise HTTPException(
                status_code=404,
                detail="Database session expired; reconnect required.",
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
            raise HTTPException(
                status_code=502,
                detail=(
                    "Database session is unavailable; reconnect required."
                ),
            ) from failure
        if response is None:
            await self._discard(session_id, session)
            raise HTTPException(
                status_code=404,
                detail="Database session expired; reconnect required.",
            )
        if response.get("type") == PipeMessageType.RESULT.value:
            return response.get(
                "result",
                WorkerResult(ResultKind.NONE),
            )
        if response.get("type") == PipeMessageType.A2A_ERROR.value:
            raise HTTPException(
                status_code=400,
                detail=response.get("detail", "A2A request failed."),
            )
        LOGGER.error("Select AI session process reported a command failure.")
        raise HTTPException(
            status_code=502,
            detail="Database session is unavailable; reconnect required.",
        )

    async def close(self, session_id: str) -> None:
        """Terminate a session on an explicit gateway DELETE request."""
        session = self.sessions.pop(session_id, None)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Database session expired; reconnect required.",
            )
        await self._terminate(session)

    async def reap_expired(self) -> None:
        """Continuously terminate expired or dead child sessions."""
        while True:
            await asyncio.sleep(_SESSION_REAPER_INTERVAL_SECONDS)
            await self._reap_expired_sessions()

    async def close_all(self) -> None:
        """Terminate all child sessions during worker shutdown."""
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
        request: OpenSessionRequest,
    ) -> None:
        try:
            response = await self._receive(
                session,
                timeout_seconds=self.session_start_timeout_seconds,
            )
        except (EOFError, OSError, TimeoutError) as error:
            raise HTTPException(
                status_code=504,
                detail="Database session start timed out.",
            ) from error
        if response.get("type") == PipeMessageType.READY.value:
            return
        detail = response.get("detail", "Database login failed.")
        for secret in (
            request.password.get_secret_value(),
            request.username,
            request.dsn,
        ):
            detail = detail.replace(secret, "[REDACTED]")
        LOGGER.error("Select AI session startup failed: %s", detail[-2_000:])
        raise HTTPException(status_code=400, detail="Database login failed.")

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


async def _register_with_consul(
    consul_url: str,
    worker_id: str,
    worker_address: str,
    worker_port: int,
    worker_endpoint: str | None = None,
) -> None:
    payload = {
        "Name": "select-ai-worker",
        "ID": worker_id,
        "Address": worker_address,
        "Port": worker_port,
        "Check": {"TTL": "30s", "DeregisterCriticalServiceAfter": "1m"},
    }
    if worker_endpoint:
        payload["Meta"] = {"endpoint": worker_endpoint.rstrip("/")}
    deadline = time.monotonic() + 30
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.put(
                    f"{consul_url}/v1/agent/service/register",
                    json=payload,
                )
            response.raise_for_status()
            return
        except httpx.HTTPError:
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(1)


async def _heartbeat(consul_url: str, worker_id: str) -> None:
    check_id = f"service:{worker_id}"
    while True:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.put(
                f"{consul_url}/v1/agent/check/pass/{check_id}"
            )
            response.raise_for_status()
        await asyncio.sleep(10)


async def _deregister_from_consul(consul_url: str, worker_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        with contextlib.suppress(httpx.HTTPError):
            await client.put(
                f"{consul_url}/v1/agent/service/deregister/{worker_id}"
            )


def create_worker_app(
    session_ttl_seconds: int = 900,
    session_start_timeout_seconds: int = 30,
) -> FastAPI:
    """Build the internal session-worker HTTP application."""
    worker = SessionWorker(session_ttl_seconds, session_start_timeout_seconds)

    consul_url = os.environ.get("CONSUL_HTTP_URL", "http://consul:8500")
    consul_url = consul_url.rstrip("/")
    worker_id = os.environ.get("WORKER_ID", socket.gethostname())
    worker_address = os.environ.get("WORKER_ADDRESS", socket.gethostname())
    worker_port = int(os.environ.get("WORKER_PORT", "8080"))
    worker_endpoint = os.environ.get("WORKER_ENDPOINT")

    @asynccontextmanager
    async def lifespan(_app):
        await _register_with_consul(
            consul_url,
            worker_id,
            worker_address,
            worker_port,
            worker_endpoint,
        )
        heartbeat = asyncio.create_task(_heartbeat(consul_url, worker_id))
        reaper = asyncio.create_task(worker.reap_expired())
        try:
            yield
        finally:
            reaper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reaper
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            await worker.close_all()
            await _deregister_from_consul(consul_url, worker_id)

    app = FastAPI(
        title="Select AI Session Worker",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/sessions", status_code=status.HTTP_201_CREATED)
    async def open_session(request: OpenSessionRequest) -> dict[str, str]:
        await worker.open(request)
        return {"status": "opened"}

    @app.post("/sessions/{session_id}/a2a")
    async def handle_a2a(
        session_id: str,
        request: Request,
    ) -> Response:
        method = request.headers.get(WORKER_A2A_METHOD_HEADER)
        if not method:
            raise HTTPException(
                status_code=400,
                detail=f"Missing {WORKER_A2A_METHOD_HEADER} header.",
            )
        result = await worker.dispatch(
            session_id,
            method,
            await request.body(),
        )
        return Response(
            content=result.payload,
            media_type=PROTOBUF_CONTENT_TYPE,
            headers={
                WORKER_RESULT_KIND_HEADER: result.kind.value,
            },
        )

    @app.delete(
        "/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def close_session(session_id: str) -> None:
        await worker.close(session_id)

    return app
