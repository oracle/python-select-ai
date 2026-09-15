# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Internal HTTP and Consul wrapper for isolated session processes."""

from __future__ import annotations

import asyncio
import contextlib
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field, SecretStr
from starlette.responses import Response

from select_ai.agent.a2a.models import WorkerSettings
from select_ai.agent.a2a.session_process import (
    ProcessSessionBackend,
    SessionBackendError,
    SessionCommandError,
    SessionLoginError,
    SessionNotFound,
    SessionSpec,
    SessionStartTimeout,
    SessionUnavailable,
)
from select_ai.agent.a2a.worker_protocol import (
    PROTOBUF_CONTENT_TYPE,
    WORKER_A2A_METHOD_HEADER,
    WORKER_RESULT_KIND_HEADER,
)


class OpenSessionRequest(BaseModel):
    """Sensitive request accepted only on the internal worker interface."""

    session_id: str
    dsn: str = Field(min_length=1, max_length=4_000)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=1_024)
    team_name: str = Field(min_length=1, max_length=128)

    def to_session_spec(self) -> SessionSpec:
        """Convert validated HTTP input to the backend-neutral contract."""
        return SessionSpec(
            session_id=self.session_id,
            dsn=self.dsn,
            username=self.username,
            password=self.password.get_secret_value(),
            team_name=self.team_name,
        )


async def _register_with_consul(
    consul_url: str,
    worker_id: str,
    worker_address: str,
    worker_port: int,
    worker_endpoint: str | None = None,
) -> None:
    payload = {
        "Name": "select-ai-a2a-worker",
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


def _http_error(error: SessionBackendError) -> HTTPException:
    """Map backend-neutral failures to the existing worker HTTP contract."""
    if isinstance(error, SessionNotFound):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, SessionStartTimeout):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    elif isinstance(error, (SessionLoginError, SessionCommandError)):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, SessionUnavailable):
        status_code = status.HTTP_502_BAD_GATEWAY
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=str(error))


def create_worker_app(settings: WorkerSettings) -> FastAPI:
    """Build the internal session-worker HTTP application."""
    backend = ProcessSessionBackend(
        settings.session_ttl_seconds,
        settings.session_start_timeout_seconds,
    )

    @asynccontextmanager
    async def lifespan(_app):
        await _register_with_consul(
            settings.consul_url,
            settings.worker_id,
            settings.worker_address,
            settings.worker_port,
            settings.worker_endpoint,
        )
        heartbeat = asyncio.create_task(
            _heartbeat(settings.consul_url, settings.worker_id)
        )
        reaper = asyncio.create_task(backend.reap_expired())
        try:
            yield
        finally:
            reaper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reaper
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            await backend.close_all()
            await _deregister_from_consul(
                settings.consul_url,
                settings.worker_id,
            )

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
        try:
            await backend.open(request.to_session_spec())
        except SessionBackendError as error:
            raise _http_error(error) from error
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
        try:
            result = await backend.dispatch(
                session_id,
                method,
                await request.body(),
            )
        except SessionBackendError as error:
            raise _http_error(error) from error
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
        try:
            await backend.close(session_id)
        except SessionBackendError as error:
            raise _http_error(error) from error

    return app
