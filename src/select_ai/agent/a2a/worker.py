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
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, SecretStr

LOGGER = logging.getLogger(__name__)


class OpenSessionRequest(BaseModel):
    """Sensitive request accepted only on the internal worker interface."""

    session_id: str
    dsn: str = Field(min_length=1, max_length=4_000)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=1_024)
    team_name: str = Field(min_length=1, max_length=128)


class PromptRequest(BaseModel):
    """One user prompt for a previously opened session."""

    prompt: str = Field(min_length=1, max_length=32_000)


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
        self.lock = asyncio.Lock()

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
        async with self.lock:
            previous = self.sessions.pop(request.session_id, None)
            if previous:
                await self._terminate(previous)
            self.sessions[request.session_id] = session

    async def get(self, session_id: str) -> ChildSession:
        """Return a live session, closing it if its expiry has elapsed."""
        async with self.lock:
            session = self.sessions.get(session_id)
            if session and (
                session.expires_at <= time.monotonic()
                or not session.process.is_alive()
            ):
                self.sessions.pop(session_id, None)
                await self._terminate(session)
                session = None
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Database session expired; reconnect required.",
            )
        return session

    async def send_prompt(self, session_id: str, prompt: str) -> str | None:
        """Run one prompt in the process that owns this database session."""
        session = await self.get(session_id)
        async with session.lock:
            if not session.process.is_alive():
                await self._discard(session_id, session)
                raise HTTPException(
                    status_code=404,
                    detail="Database session expired; reconnect required.",
                )
            try:
                await asyncio.to_thread(
                    session.connection.send,
                    {"type": "run", "prompt": prompt},
                )
                response = await self._receive(session, timeout_seconds=120)
            except (EOFError, OSError, TimeoutError) as error:
                await self._discard(session_id, session)
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Database session is unavailable; reconnect required."
                    ),
                ) from error
        if response.get("type") == "result":
            return response.get("result")
        LOGGER.error("Select AI session process reported a command failure.")
        raise HTTPException(
            status_code=502,
            detail="Database session is unavailable; reconnect required.",
        )

    async def close(self, session_id: str) -> None:
        """Terminate a session on an explicit gateway DELETE request."""
        async with self.lock:
            session = self.sessions.pop(session_id, None)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Database session expired; reconnect required.",
            )
        await self._terminate(session)

    async def close_all(self) -> None:
        """Terminate all child sessions during worker shutdown."""
        async with self.lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for session in sessions:
            await self._terminate(session)

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
        if response.get("type") == "ready":
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
        async with self.lock:
            if self.sessions.get(session_id) is session:
                self.sessions.pop(session_id, None)
        await self._terminate(session)

    @staticmethod
    async def _terminate(session: ChildSession) -> None:
        def stop() -> None:
            try:
                if session.process.is_alive():
                    with contextlib.suppress(OSError):
                        session.connection.send({"type": "close"})
                    session.process.join(timeout=5)
                if session.process.is_alive():
                    session.process.terminate()
                    session.process.join(timeout=5)
            finally:
                session.connection.close()

        await asyncio.to_thread(stop)


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
    """Open one async connection and execute raw ``AsyncTeam`` prompts."""
    import select_ai
    from select_ai.agent import AsyncTeam

    ready = False
    try:
        await select_ai.async_connect(
            user=credentials["user"],
            password=credentials["password"],
            dsn=credentials["dsn"],
        )
        if not await select_ai.async_is_connected():
            raise RuntimeError("Database login failed.")
        connection.send({"type": "ready"})
        ready = True
        conversation_id = None
        while True:
            try:
                command = await asyncio.to_thread(connection.recv)
            except EOFError:
                return
            if command.get("type") == "close":
                return
            if command.get("type") != "run":
                connection.send(
                    {"type": "error", "detail": "Invalid command."}
                )
                continue
            try:
                if conversation_id is None:
                    conversation = select_ai.AsyncConversation(
                        attributes=select_ai.ConversationAttributes(
                            title=f"A2A {team_name}",
                            description=f"Temporary session {session_id}",
                        )
                    )
                    conversation_id = await conversation.create()
                result = await AsyncTeam(team_name=team_name).run(
                    prompt=command["prompt"],
                    params={"conversation_id": conversation_id},
                )
                connection.send({"type": "result", "result": result})
            except Exception:
                # Keep session-process failures private from gateway callers.
                LOGGER.error("Select AI session command failed")
                connection.send({"type": "error"})
    except Exception as error:
        LOGGER.error("Select AI session process startup failed")
        if not ready:
            with contextlib.suppress(OSError):
                connection.send({"type": "error", "detail": str(error)})
    finally:
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
        try:
            yield
        finally:
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

    @app.post("/sessions/{session_id}/messages")
    async def send_message(
        session_id: str,
        request: PromptRequest,
    ) -> PlainTextResponse:
        result = await worker.send_prompt(session_id, request.prompt)
        return PlainTextResponse(result or "")

    @app.delete(
        "/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def close_session(session_id: str) -> None:
        await worker.close(session_id)

    return app
