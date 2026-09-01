# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Configuration and transient request models for the A2A runtime."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GatewaySettings:
    """Configuration for the public gateway process."""

    agent_url: str
    consul_url: str
    worker_service: str
    session_ttl_seconds: int
    worker_tls_ca_file: str | None = None
    worker_tls_cert_file: str | None = None
    worker_tls_key_file: str | None = None

    def __post_init__(self) -> None:
        if self.session_ttl_seconds < 1:
            raise ValueError("session_ttl_seconds must be at least 1")
        tls_files = (
            self.worker_tls_ca_file,
            self.worker_tls_cert_file,
            self.worker_tls_key_file,
        )
        if any(tls_files) and not all(tls_files):
            raise ValueError(
                "worker mTLS requires a CA file, client certificate, and "
                "client key."
            )
        object.__setattr__(self, "agent_url", self.agent_url.rstrip("/"))
        object.__setattr__(self, "consul_url", self.consul_url.rstrip("/"))

    @property
    def worker_mtls_enabled(self) -> bool:
        """Whether gateway-to-worker calls require mutual TLS."""
        return self.worker_tls_ca_file is not None


@dataclass(frozen=True)
class SessionInfo:
    """Credentials used only while opening one in-memory worker session."""

    dsn: str
    username: str
    password: str
    team_name: str

    @classmethod
    def from_a2ui_event(cls, event: dict) -> "SessionInfo":
        required = ("dsn", "username", "password", "team_name")
        if not all(
            isinstance(event.get(key), str) and event[key] for key in required
        ):
            raise ValueError("All database connection fields are required.")
        return cls(**{key: event[key] for key in required})


@dataclass(frozen=True)
class SessionRoute:
    """Non-secret Consul record that routes a session to one worker."""

    endpoint: str
    expires_at: float
