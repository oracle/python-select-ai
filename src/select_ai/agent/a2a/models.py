# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Configuration and transient request models for the A2A runtime."""

from dataclasses import dataclass, field

CONNECTION_FIELDS = ("dsn", "username", "password", "team_name")


@dataclass(frozen=True)
class ConnectionConfig:
    """Deployment-provided values for a database session."""

    dsn: str | None = None
    username: str | None = None
    password: str | None = None
    team_name: str | None = None

    def __post_init__(self) -> None:
        for name in CONNECTION_FIELDS:
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} must be a non-empty string")

    @property
    def missing_fields(self) -> tuple[str, ...]:
        """Return canonical properties that must come from the form."""
        return tuple(
            name for name in CONNECTION_FIELDS if getattr(self, name) is None
        )

    def resolve(self, submitted: dict) -> "SessionInfo":
        """Merge validated submitted values with immutable server values."""
        if not isinstance(submitted, dict):
            raise ValueError("Connection form context must be an object.")
        unknown = set(submitted) - set(CONNECTION_FIELDS)
        if unknown:
            raise ValueError("Connection form contains unsupported fields.")
        configured = {
            name
            for name in CONNECTION_FIELDS
            if getattr(self, name) is not None
        }
        if configured.intersection(submitted):
            raise ValueError(
                "Configured connection fields cannot be overridden."
            )
        values = {
            name: getattr(self, name, None) or submitted.get(name)
            for name in CONNECTION_FIELDS
        }
        return SessionInfo.from_values(values)


@dataclass(frozen=True)
class WorkerSettings:
    """Configuration for the internal session worker."""

    consul_url: str
    worker_id: str
    worker_address: str
    worker_port: int
    session_ttl_seconds: int
    session_start_timeout_seconds: int
    worker_endpoint: str | None = None

    def __post_init__(self) -> None:
        if self.worker_port < 1 or self.worker_port > 65_535:
            raise ValueError("worker_port must be between 1 and 65535")
        if self.session_ttl_seconds < 1:
            raise ValueError("session_ttl_seconds must be at least 1")
        if self.session_start_timeout_seconds < 1:
            raise ValueError(
                "session_start_timeout_seconds must be at least 1"
            )
        object.__setattr__(self, "consul_url", self.consul_url.rstrip("/"))
        if self.worker_endpoint:
            object.__setattr__(
                self,
                "worker_endpoint",
                self.worker_endpoint.rstrip("/"),
            )


@dataclass(frozen=True)
class GatewaySettings:
    """Configuration for the public gateway process."""

    public_url: str
    consul_url: str
    worker_service: str
    session_ttl_seconds: int
    worker_tls_ca_file: str | None = None
    worker_tls_cert_file: str | None = None
    worker_tls_key_file: str | None = None
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    connection_form_template: tuple[dict, ...] | None = None

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
        object.__setattr__(self, "public_url", self.public_url.rstrip("/"))
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
    def from_values(cls, values: dict) -> "SessionInfo":
        """Build a complete connection after resolution."""
        if not all(
            isinstance(values.get(key), str) and values[key]
            for key in CONNECTION_FIELDS
        ):
            raise ValueError("All database connection fields are required.")
        return cls(**{key: values[key] for key in CONNECTION_FIELDS})


@dataclass(frozen=True)
class SessionRoute:
    """Non-secret Consul record that routes a session to one worker."""

    endpoint: str
    expires_at: float
