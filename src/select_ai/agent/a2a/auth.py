# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Authentication integration for public A2A Starlette applications."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json

from a2a.types import (
    AgentCard,
    HTTPAuthSecurityScheme,
    SecurityScheme,
    StringList,
)
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse


class TrustedBearerAuthenticationBackend(AuthenticationBackend):
    """Map an upstream-validated OAuth bearer token to a Starlette user.

    Signature and claims validation belongs to the deployment's authenticating
    proxy (for example Gemini Enterprise). This backend only establishes the
    SDK user object from the already trusted token.
    """

    async def authenticate(self, connection):
        header = connection.headers.get("authorization")
        if header is None:
            return None
        scheme, separator, token = header.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Authorization must use Bearer syntax.")
        owner = _bearer_owner(token)
        return AuthCredentials(["authenticated"]), SimpleUser(owner)


class RequireA2AAuthenticationMiddleware:
    """Require an SDK-visible user on the JSON-RPC endpoint."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] == "http"
            and scope.get("path", "").rstrip("/") == "/a2a/jsonrpc"
            and not scope["user"].is_authenticated
        ):
            response = JSONResponse(
                {"detail": "Bearer authentication is required."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def authentication_middleware(require_oauth: bool) -> list[Middleware]:
    """Enable bearer authentication only when explicitly requested."""
    if not require_oauth:
        return []
    return [
        Middleware(
            AuthenticationMiddleware,
            backend=TrustedBearerAuthenticationBackend(),
            on_error=_authentication_error,
        ),
        Middleware(
            RequireA2AAuthenticationMiddleware,
        ),
    ]


def add_bearer_security(agent_card: AgentCard) -> None:
    """Advertise the bearer contract on an authenticated Agent Card."""
    agent_card.security_schemes["bearer"].CopyFrom(
        SecurityScheme(
            http_auth_security_scheme=HTTPAuthSecurityScheme(
                description=(
                    "Upstream-validated end-user OAuth 2.0 access token or "
                    "OpenID Connect ID token."
                ),
                scheme="bearer",
            )
        )
    )
    requirement = agent_card.security_requirements.add()
    requirement.schemes["bearer"].CopyFrom(StringList())


def _authentication_error(_connection, error):
    return JSONResponse(
        {"detail": str(error)},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_owner(token: str) -> str:
    """Derive an opaque owner from a trusted JWT or OAuth access token."""
    jwt_owner = _jwt_owner(token)
    if jwt_owner is not None:
        return jwt_owner
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"oauth:{digest}"


def _jwt_owner(token: str) -> str | None:
    """Return the issuer/subject owner when the bearer value is a JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        encoded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded))
    except (
        binascii.Error,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ):
        return None
    subject = payload.get("sub") if isinstance(payload, dict) else None
    issuer = payload.get("iss") if isinstance(payload, dict) else None
    if not isinstance(subject, str) or not subject:
        return None
    if not isinstance(issuer, str) or not issuer:
        return None
    digest = hashlib.sha256(f"{issuer}\0{subject}".encode("utf-8")).hexdigest()
    return f"jwt:{digest}"
