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
import time
from threading import Lock

import requests

from select_ai.agent.a2a import GatewaySettings, SessionInfo, SessionRoute


class ReconnectRequired(RuntimeError):
    """The worker no longer owns the requested in-memory session."""


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

    def send_prompt(self, session_id: str, prompt: str) -> str | None:
        """Forward a prompt and return the worker's raw team result."""
        route = self._route_for(session_id)
        response = requests.post(
            f"{route.endpoint}/sessions/{session_id}/messages",
            json={"prompt": prompt},
            timeout=130,
            **getattr(self, "_worker_request_kwargs", {}),
        )
        if response.status_code in (404, 502):
            self._close_worker_session(route, session_id)
            raise ReconnectRequired(
                "Database session ended; reconnect required."
            )
        response.raise_for_status()
        return response.text or None

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
        endpoint = service.get("Meta", {}).get("endpoint")
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
            f"{self.settings.consul_url}/v1/kv/select-ai/sessions/"
            f"{session_id}",
            timeout=10,
        )
        if response.status_code == 404:
            raise ReconnectRequired(
                "Database session expired; reconnect required."
            )
        response.raise_for_status()
        value = response.json()[0]["Value"]
        route = SessionRoute(**json.loads(base64.b64decode(value).decode()))
        if route.expires_at <= time.time():
            self._close_worker_session(route, session_id)
            raise ReconnectRequired(
                "Database session expired; reconnect required."
            )
        return route

    def _save_route(self, session_id: str, route: SessionRoute) -> bool:
        response = requests.put(
            f"{self.settings.consul_url}/v1/kv/select-ai/sessions/"
            f"{session_id}?cas=0",
            data=json.dumps(route.__dict__),
            timeout=10,
        )
        return response.ok and response.text.strip().lower() == "true"

    def _delete_route(self, session_id: str) -> None:
        requests.delete(
            f"{self.settings.consul_url}/v1/kv/select-ai/sessions/"
            f"{session_id}",
            timeout=10,
        )

    def _close_worker_session(
        self,
        route: SessionRoute,
        session_id: str,
    ) -> None:
        try:
            response = requests.delete(
                f"{route.endpoint}/sessions/{session_id}",
                timeout=10,
                **getattr(self, "_worker_request_kwargs", {}),
            )
            if response.status_code != 404:
                response.raise_for_status()
        except requests.RequestException:
            pass
        finally:
            self._delete_route(session_id)
