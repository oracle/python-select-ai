# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Consul-backed routing client for the internal session worker."""

from __future__ import annotations

import base64
import json
import logging
import time
from threading import Lock
from urllib.parse import quote

import requests
from a2a.types.a2a_pb2 import (
    CancelTaskRequest,
    GetTaskRequest,
    ListTasksRequest,
    ListTasksResponse,
    Message,
    SendMessageRequest,
    Task,
)

from select_ai.agent.a2a import GatewaySettings, SessionInfo, SessionRoute
from select_ai.agent.a2a.worker_protocol import (
    PROTOBUF_CONTENT_TYPE,
    WORKER_A2A_METHOD_HEADER,
    WORKER_RESULT_KIND_HEADER,
    A2AMethod,
    ResultKind,
    WorkerResult,
    decode_result,
)

LOGGER = logging.getLogger(__name__)

_SESSION_PREFIX = "select-ai/sessions/"
_TASK_PREFIX = "select-ai/tasks/"


class ReconnectRequired(RuntimeError):
    """The worker no longer owns the requested in-memory session."""

    def __init__(self, message: str, session_id: str | None = None):
        super().__init__(message)
        self.session_id = session_id


class WorkerClient:
    """Open, route, and close short-lived Select AI worker sessions."""

    def __init__(self, settings: GatewaySettings):
        self.settings = settings
        self._selection_lock = Lock()
        self._next_worker = 0
        self._worker_request_kwargs: dict[str, object] = {}
        if settings.worker_mtls_enabled:
            self._worker_request_kwargs = {
                "verify": settings.worker_tls_ca_file,
                "cert": (
                    settings.worker_tls_cert_file,
                    settings.worker_tls_key_file,
                ),
            }

    def open_session(self, session_id: str, session_info: SessionInfo) -> str:
        """Open a session and save a non-secret route in Consul."""
        endpoint = self._select_worker()
        response = requests.post(
            f"{endpoint}/sessions",
            json={"session_id": session_id, **session_info.__dict__},
            timeout=45,
            **self._worker_request_kwargs,
        )
        response.raise_for_status()
        route = SessionRoute(
            endpoint=endpoint,
            expires_at=time.time() + self.settings.session_ttl_seconds,
        )
        if not self._save_route(session_id, route):
            self._close_worker_session(route, session_id)
            raise RuntimeError("Could not create the database session.")
        return session_id

    def send_message(
        self,
        session_id: str,
        request: SendMessageRequest,
    ) -> Task | Message | None:
        """Forward one A2A message to the worker session."""
        result = self._dispatch(
            session_id,
            A2AMethod.SEND_MESSAGE,
            request,
        )
        value = decode_result(result)
        if isinstance(value, Task):
            self._save_task_route(value.id, session_id)
        return value

    def get_task(self, params: GetTaskRequest) -> Task | None:
        """Retrieve a task from its owning worker session."""
        session_id = self.task_session_id(params.id)
        if session_id is None:
            return None
        result = self._dispatch(session_id, A2AMethod.GET_TASK, params)
        value = decode_result(result)
        if isinstance(value, Task):
            return value
        return None

    def list_tasks(
        self,
        session_id: str,
        params: ListTasksRequest,
    ) -> ListTasksResponse:
        """Retrieve one session's database-paginated task response."""
        result = self._dispatch(
            session_id,
            A2AMethod.LIST_TASKS,
            params,
        )
        return decode_result(result) or ListTasksResponse()

    def cancel_task(self, task_id: str) -> Task | None:
        """Cancel a task in the worker that owns it."""
        session_id = self.task_session_id(task_id)
        if session_id is None:
            return None
        result = self._dispatch(
            session_id,
            A2AMethod.CANCEL_TASK,
            CancelTaskRequest(id=task_id),
        )
        value = decode_result(result)
        return value if isinstance(value, Task) else None

    def delete_task(self, task_id: str) -> None:
        """Delete a task and its routing metadata."""
        session_id = self.task_session_id(task_id)
        if session_id:
            try:
                self._dispatch(
                    session_id,
                    A2AMethod.DELETE_TASK,
                    GetTaskRequest(id=task_id),
                )
            except ReconnectRequired:
                pass
        self._delete_task_route(task_id)

    def session_exists(self, session_id: str) -> bool:
        """Return whether Consul still has a live route for a session."""
        try:
            self._route_for(session_id)
        except ReconnectRequired:
            return False
        return True

    def task_session_id(self, task_id: str) -> str | None:
        """Return the worker session recorded for a task, if any."""
        response = requests.get(
            f"{self.settings.consul_url}/v1/kv/{_TASK_PREFIX}"
            f"{quote(task_id, safe='')}",
            timeout=10,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        values = response.json() or []
        if not values or not values[0].get("Value"):
            return None
        return base64.b64decode(values[0]["Value"]).decode()

    def _dispatch(
        self,
        session_id: str,
        method: A2AMethod | str,
        message,
    ) -> WorkerResult:
        """Send one protobuf-serialized A2A operation to a worker session."""
        route = self._route_for(session_id)
        response = requests.post(
            f"{route.endpoint}/sessions/{quote(session_id, safe='')}/a2a",
            data=message.SerializeToString(),
            headers={
                "content-type": PROTOBUF_CONTENT_TYPE,
                WORKER_A2A_METHOD_HEADER: A2AMethod(method).value,
            },
            timeout=130,
            **getattr(self, "_worker_request_kwargs", {}),
        )
        if response.status_code in (404, 502):
            self._close_worker_session(route, session_id)
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                session_id,
            )
        response.raise_for_status()
        return WorkerResult(
            kind=ResultKind(
                response.headers.get(
                    WORKER_RESULT_KIND_HEADER,
                    ResultKind.NONE.value,
                )
            ),
            payload=response.content,
        )

    def _save_task_route(self, task_id: str, session_id: str) -> None:
        """Save only task-to-session routing metadata in Consul."""
        try:
            response = requests.put(
                f"{self.settings.consul_url}/v1/kv/{_TASK_PREFIX}"
                f"{quote(task_id, safe='')}",
                data=session_id,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            # The task itself is already durable in Oracle, but task routes
            # are required because workers may use different databases.
            LOGGER.warning("Could not save route for task %s", task_id)

    def _delete_task_route(self, task_id: str) -> None:
        requests.delete(
            f"{self.settings.consul_url}/v1/kv/{_TASK_PREFIX}"
            f"{quote(task_id, safe='')}",
            timeout=10,
        )

    def close_session(self, session_id: str) -> None:
        """Close the child process and remove the Consul route."""
        try:
            route = self._route_for(session_id)
        except ReconnectRequired:
            self._delete_route(session_id)
            return
        self._close_worker_session(route, session_id)

    def _select_worker(self) -> str:
        response = requests.get(
            f"{self.settings.consul_url}/v1/health/service/"
            f"{self.settings.worker_service}",
            params={"passing": "true"},
            timeout=10,
        )
        response.raise_for_status()
        workers = response.json()
        if not workers:
            raise RuntimeError("No healthy Select AI workers are available.")
        with self._selection_lock:
            worker = workers[self._next_worker % len(workers)]
            self._next_worker += 1
        service = worker["Service"]
        metadata = service.get("Meta") or {}
        endpoint = metadata.get("endpoint")
        if endpoint:
            endpoint = endpoint.rstrip("/")
            if self.settings.worker_mtls_enabled and not endpoint.startswith(
                "https://"
            ):
                raise RuntimeError(
                    "A worker registered a non-HTTPS endpoint while mTLS is "
                    "required."
                )
            return endpoint
        if self.settings.worker_mtls_enabled:
            raise RuntimeError(
                "Workers must register an HTTPS endpoint while mTLS is "
                "required."
            )
        address = service.get("Address") or worker["Node"]["Address"]
        return f"http://{address}:{service['Port']}"

    def _route_for(self, session_id: str) -> SessionRoute:
        response = requests.get(
            f"{self.settings.consul_url}/v1/kv/{_SESSION_PREFIX}"
            f"{quote(session_id, safe='')}",
            timeout=10,
        )
        if response.status_code == 404:
            raise ReconnectRequired(
                "Database session expired; reconnect required.",
                session_id,
            )
        response.raise_for_status()
        value = response.json()[0]["Value"]
        route = SessionRoute(**json.loads(base64.b64decode(value).decode()))
        if route.expires_at <= time.time():
            self._close_worker_session(route, session_id)
            raise ReconnectRequired(
                "Database session expired; reconnect required.",
                session_id,
            )
        return route

    def _save_route(self, session_id: str, route: SessionRoute) -> bool:
        response = requests.put(
            f"{self.settings.consul_url}/v1/kv/{_SESSION_PREFIX}"
            f"{quote(session_id, safe='')}?cas=0",
            data=json.dumps(route.__dict__),
            timeout=10,
        )
        return response.ok and response.text.strip().lower() == "true"

    def _delete_route(self, session_id: str) -> None:
        requests.delete(
            f"{self.settings.consul_url}/v1/kv/{_SESSION_PREFIX}"
            f"{quote(session_id, safe='')}",
            timeout=10,
        )

    def _close_worker_session(
        self,
        route: SessionRoute,
        session_id: str,
    ) -> None:
        try:
            response = requests.delete(
                f"{route.endpoint}/sessions/{quote(session_id, safe='')}",
                timeout=10,
                **getattr(self, "_worker_request_kwargs", {}),
            )
            if response.status_code != 404:
                response.raise_for_status()
        except requests.RequestException:
            pass
        finally:
            self._delete_route(session_id)
