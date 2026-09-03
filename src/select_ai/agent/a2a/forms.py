# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A2UI connection form emitted by the public gateway."""

from uuid import uuid4

from select_ai.agent.a2a.a2ui import A2UI_CATALOG_ID, A2UI_VERSION


def connection_form(surface_id: str | None = None) -> list[dict]:
    """Return the non-persistent database connection form."""
    # A2UI surface IDs must be globally unique for the renderer's lifetime.
    # Gemini retains surfaces for an A2A conversation after the connection
    # form is submitted, so reusing a fixed ID prevents a reconnect form from
    # being created in that same conversation.
    surface_id = surface_id or f"db-connect-{uuid4().hex}"
    return [
        {
            "version": A2UI_VERSION,
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": [
                    {"id": "root", "component": "Card", "child": "column"},
                    {
                        "id": "column",
                        "component": "Column",
                        "children": [
                            "title",
                            "dsn",
                            "user",
                            "password",
                            "team",
                            "connect",
                        ],
                    },
                    {
                        "id": "title",
                        "component": "Text",
                        "text": "Connect to Oracle Database",
                        "variant": "h2",
                    },
                    {
                        "id": "dsn",
                        "component": "TextField",
                        "label": "Database DSN",
                        "value": {"path": "/dsn"},
                        "variant": "shortText",
                    },
                    {
                        "id": "user",
                        "component": "TextField",
                        "label": "Database username",
                        "value": {"path": "/username"},
                        "variant": "shortText",
                    },
                    {
                        "id": "password",
                        "component": "TextField",
                        "label": "Database password",
                        "value": {"path": "/password"},
                        "variant": "obscured",
                    },
                    {
                        "id": "team",
                        "component": "TextField",
                        "label": "Select AI team name",
                        "value": {"path": "/team_name"},
                        "variant": "shortText",
                    },
                    {
                        "id": "connect_label",
                        "component": "Text",
                        "text": "Connect",
                    },
                    {
                        "id": "connect",
                        "component": "Button",
                        "child": "connect_label",
                        "variant": "primary",
                        "action": {
                            "event": {
                                "name": "submit_database_connection",
                                "context": {
                                    "dsn": {"path": "/dsn"},
                                    "username": {"path": "/username"},
                                    "password": {"path": "/password"},
                                    "team_name": {"path": "/team_name"},
                                },
                            }
                        },
                    },
                ],
            },
        },
        {
            "version": A2UI_VERSION,
            "updateDataModel": {
                "surfaceId": surface_id,
                "path": "/",
                "value": {
                    "dsn": "",
                    "username": "",
                    "password": "",
                    "team_name": "",
                },
            },
        },
    ]
