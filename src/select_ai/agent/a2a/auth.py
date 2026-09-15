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
    """Map an upstream-validated bearer JWT's ``sub`` to a Starlette user.

    Signature and claims validation belongs to the deployment's authenticating
    proxy (for example Gemini Enterprise plus Cloud Run IAM). This backend only
    establishes the SDK user object from the already trusted token.
    """

    async def authenticate(self, connection):
        header = connection.headers.get("authorization")
        if header is None:
            return None
        scheme, separator, token = header.partition(" ")
        if separator != " " or scheme.lower() != "bearer" or not token:
            raise AuthenticationError("Authorization must use Bearer syntax.")
        owner = _jwt_owner(token)
        return AuthCredentials(["authenticated"]), SimpleUser(owner)


class RequireA2AAuthenticationMiddleware:
    """Require an SDK-visible user on the JSON-RPC endpoint."""

    def __init__(self, app, allow_unauthenticated: bool = False) -> None:
        self.app = app
        self.allow_unauthenticated = allow_unauthenticated

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] == "http"
            and scope.get("path", "").rstrip("/") == "/a2a/jsonrpc"
            and not self.allow_unauthenticated
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


def authentication_middleware(
    allow_unauthenticated: bool,
) -> list[Middleware]:
    """Return middleware ordered so authentication precedes enforcement."""
    return [
        Middleware(
            AuthenticationMiddleware,
            backend=TrustedBearerAuthenticationBackend(),
            on_error=_authentication_error,
        ),
        Middleware(
            RequireA2AAuthenticationMiddleware,
            allow_unauthenticated=allow_unauthenticated,
        ),
    ]


def add_bearer_security(agent_card: AgentCard) -> None:
    """Advertise the bearer contract on an authenticated Agent Card."""
    agent_card.security_schemes["bearer"].CopyFrom(
        SecurityScheme(
            http_auth_security_scheme=HTTPAuthSecurityScheme(
                description="Upstream-validated user identity token.",
                scheme="bearer",
                bearer_format="JWT",
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


def _jwt_owner(token: str) -> str:
    """Derive a stable opaque owner from an upstream-validated JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Bearer token must be a JWT.")
    try:
        encoded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded))
    except (
        binascii.Error,
        UnicodeDecodeError,
        ValueError,
        TypeError,
    ) as error:
        raise AuthenticationError(
            "Bearer token has an invalid payload."
        ) from error
    subject = payload.get("sub") if isinstance(payload, dict) else None
    issuer = payload.get("iss") if isinstance(payload, dict) else None
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("Bearer token has no subject.")
    if not isinstance(issuer, str) or not issuer:
        raise AuthenticationError("Bearer token has no issuer.")
    digest = hashlib.sha256(f"{issuer}\0{subject}".encode("utf-8")).hexdigest()
    return f"jwt:{digest}"
