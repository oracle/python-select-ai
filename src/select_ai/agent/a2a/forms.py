# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Generation and validation for the A2UI database connection form."""

from __future__ import annotations

import json
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from select_ai.agent.a2a.a2ui import A2UI_CATALOG_ID, A2UI_VERSION
from select_ai.agent.a2a.models import CONNECTION_FIELDS

_ACTION_NAME = "submit_database_connection"
_FIELD_COMPONENTS = {
    "dsn": ("Database DSN", "shortText"),
    "username": ("Database username", "shortText"),
    "password": ("Database password", "obscured"),
    "team_name": ("Select AI team name", "shortText"),
}


def connection_form(
    surface_id: str | None = None,
    missing_fields: Iterable[str] | None = None,
    template: tuple[dict, ...] | None = None,
) -> list[dict]:
    """Return a fresh form containing only missing connection properties."""
    fields = (
        tuple(CONNECTION_FIELDS)
        if missing_fields is None
        else tuple(missing_fields)
    )
    if not fields:
        return []
    if set(fields) - set(CONNECTION_FIELDS):
        raise ValueError("Connection form contains unsupported fields.")
    surface_id = surface_id or f"db-connect-{uuid4().hex}"
    if template is not None:
        return _rebind_surface(template, surface_id)

    field_components = [
        {
            "id": field,
            "component": "TextField",
            "label": _FIELD_COMPONENTS[field][0],
            "value": {"path": f"/{field}"},
            "variant": _FIELD_COMPONENTS[field][1],
        }
        for field in fields
    ]
    action_context = {field: {"path": f"/{field}"} for field in fields}
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
                        "children": ["title", *fields, "connect"],
                    },
                    {
                        "id": "title",
                        "component": "Text",
                        "text": "Connect to Oracle Database",
                        "variant": "h2",
                    },
                    *field_components,
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
                                "name": _ACTION_NAME,
                                "context": action_context,
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
                "value": {field: "" for field in fields},
            },
        },
    ]


def load_connection_form(
    path: str,
    missing_fields: Iterable[str],
) -> tuple[dict, ...]:
    """Load and validate one custom A2UI form template."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load A2UI form: {error}") from error
    return validate_connection_form(value, missing_fields)


def validate_connection_form(
    operations,
    missing_fields: Iterable[str],
) -> tuple[dict, ...]:
    """Validate the supported custom connection-form contract."""
    fields = tuple(missing_fields)
    if not isinstance(operations, list) or not operations:
        raise ValueError("A2UI form must be a non-empty JSON array.")
    if not all(isinstance(operation, dict) for operation in operations):
        raise ValueError("Every A2UI form operation must be an object.")
    if any(
        operation.get("version") != A2UI_VERSION for operation in operations
    ):
        raise ValueError(f"Every A2UI operation must use {A2UI_VERSION}.")

    surface_ids = set()
    actions = []
    has_catalog = False
    password_is_obscured = False
    for operation in operations:
        for value in operation.values():
            if isinstance(value, dict) and value.get("surfaceId"):
                surface_ids.add(value["surfaceId"])
        created = operation.get("createSurface")
        if isinstance(created, dict):
            has_catalog = created.get("catalogId") == A2UI_CATALOG_ID
        updated = operation.get("updateComponents")
        if isinstance(updated, dict):
            for component in updated.get("components") or []:
                if not isinstance(component, dict):
                    continue
                event = (component.get("action") or {}).get("event")
                if (
                    isinstance(event, dict)
                    and event.get("name") == _ACTION_NAME
                ):
                    actions.append(event)
                if (
                    component.get("component") == "TextField"
                    and component.get("value") == {"path": "/password"}
                    and component.get("variant") == "obscured"
                ):
                    password_is_obscured = True
        data_model = operation.get("updateDataModel")
        if isinstance(data_model, dict):
            value = data_model.get("value")
            if isinstance(value, dict) and value.get("password"):
                raise ValueError("A2UI form must not embed a password value.")

    if not has_catalog:
        raise ValueError(
            "A2UI form must create the advertised catalog surface."
        )
    if len(surface_ids) != 1:
        raise ValueError(
            "A2UI form must use one consistent template surfaceId."
        )
    if len(actions) != 1:
        raise ValueError(
            f"A2UI form must contain exactly one {_ACTION_NAME} action."
        )
    context = actions[0].get("context")
    if not isinstance(context, dict) or set(context) != set(fields):
        raise ValueError(
            "A2UI form action must submit exactly the missing fields."
        )
    if any(context[field] != {"path": f"/{field}"} for field in fields):
        raise ValueError(
            "A2UI form action uses an invalid connection field path."
        )
    if "password" in fields and not password_is_obscured:
        raise ValueError("A2UI password input must use the obscured variant.")
    return tuple(deepcopy(operations))


def _rebind_surface(template: tuple[dict, ...], surface_id: str) -> list[dict]:
    operations = deepcopy(list(template))

    def replace(value) -> None:
        if isinstance(value, dict):
            if "surfaceId" in value:
                value["surfaceId"] = surface_id
            for child in value.values():
                replace(child)
        elif isinstance(value, list):
            for child in value:
                replace(child)

    replace(operations)
    return operations
