# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""A2UI connection form emitted by the public gateway."""


_CATALOG = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/"
    "gemini_enterprise_composite_catalog.json"
)


def connection_form() -> list[dict]:
    """Return the non-persistent database connection form."""
    return [
        {
            "version": "v0.9",
            "createSurface": {
                "surfaceId": "db-connect",
                "catalogId": _CATALOG,
            },
        },
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "db-connect",
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
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": "db-connect",
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
