# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import asyncio
import json

import pytest

pytest.importorskip("a2a")

from select_ai.agent.a2a.server import (
    _build_agent_card,
    _build_v03_agent_card,
    create_app,
)


def test_v03_discovery_card_is_gemini_enterprise_compatible():
    card = _build_agent_card(
        team_name="ORACLE_AI_DATABASE_AGENT",
        public_url="https://agent.example.com",
        description=None,
    )

    payload = _build_v03_agent_card(card)

    assert payload["protocolVersion"] == "0.3"
    assert payload["url"] == "https://agent.example.com/a2a/jsonrpc/"
    assert "supportedInterfaces" not in payload


def test_discovery_route_serves_only_the_v03_agent_card():
    app = create_app(
        team_name="ORACLE_AI_DATABASE_AGENT",
        public_url="https://agent.example.com",
        user="user",
        password="password",
        dsn="database",
    )
    route = next(
        route
        for route in app.routes
        if route.path == "/.well-known/agent-card.json"
    )

    response = asyncio.run(route.endpoint(None))
    payload = json.loads(response.body)

    assert payload["protocolVersion"] == "0.3"
    assert payload["url"] == "https://agent.example.com/a2a/jsonrpc/"
    assert "supportedInterfaces" not in payload
