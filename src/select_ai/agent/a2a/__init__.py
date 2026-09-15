# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A2A support for Select AI Agent Teams and temporary sessions."""

from .models import (
    ConnectionConfig,
    GatewaySettings,
    SessionInfo,
    SessionRoute,
    WorkerSettings,
)


def create_gateway_app(settings):
    """Build the public A2A/A2UI gateway application."""
    from select_ai.agent.a2a.gateway import create_gateway_app as factory

    return factory(settings)


def create_worker_app(settings: WorkerSettings):
    """Build the internal worker application."""
    from select_ai.agent.a2a.worker import create_worker_app as factory

    return factory(settings)


__all__ = [
    "GatewaySettings",
    "ConnectionConfig",
    "SessionInfo",
    "SessionRoute",
    "WorkerSettings",
    "create_gateway_app",
    "create_worker_app",
]
