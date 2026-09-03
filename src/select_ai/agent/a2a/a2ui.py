# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Shared A2UI protocol helpers for Select AI A2A agents."""

from __future__ import annotations

from collections.abc import Iterator

from a2a.helpers import new_data_part
from a2a.types import AgentExtension
from a2a.types.a2a_pb2 import Message, Part
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Struct

A2UI_VERSION = "v0.9"
A2UI_EXTENSION_URI = f"https://a2ui.org/a2a-extension/a2ui/{A2UI_VERSION}"
A2UI_MIME_TYPE = "application/json+a2ui"
A2UI_CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/"
    f"{A2UI_VERSION.replace('.', '_')}/"
    "gemini_enterprise_composite_catalog.json"
)


def a2ui_extension() -> AgentExtension:
    """Return the supported A2UI capability used by Gemini Enterprise."""
    params = ParseDict(
        {
            "acceptsInlineCatalogs": True,
            "supportedCatalogIds": [A2UI_CATALOG_ID],
        },
        Struct(),
    )
    return AgentExtension(
        uri=A2UI_EXTENSION_URI,
        description="Provides agent driven UI using the A2UI JSON format.",
        params=params,
    )


def a2ui_part(operation: dict) -> Part:
    """Encode one A2UI operation in an A2A data part."""
    part = new_data_part(operation)
    ParseDict({"mimeType": A2UI_MIME_TYPE}, part.metadata)
    return part


def a2ui_operations(message: Message) -> Iterator[dict]:
    """Yield operations from data parts marked with the A2UI MIME type."""
    for part in message.parts:
        if not _is_a2ui_part(part):
            continue
        data = MessageToDict(part.data)
        operations = data if isinstance(data, list) else [data]
        yield from (
            operation
            for operation in operations
            if isinstance(operation, dict)
        )


def find_action(message: Message, name: str) -> dict | None:
    """Return a named A2UI action, including Gemini's unmarked input form."""
    for part in message.parts:
        if part.WhichOneof("content") != "data":
            continue
        mime_type = MessageToDict(part.metadata).get("mimeType")
        # Gemini Enterprise does not currently echo the A2UI MIME metadata on
        # a submitted form action.  Accept that legacy input shape, while
        # still rejecting data parts explicitly marked as another format.
        if mime_type not in (None, A2UI_MIME_TYPE):
            continue
        data = MessageToDict(part.data)
        operations = data if isinstance(data, list) else [data]
        for operation in operations:
            if (
                not isinstance(operation, dict)
                or operation.get("version") != A2UI_VERSION
            ):
                continue
            action = operation.get("action")
            if isinstance(action, dict) and action.get("name") == name:
                return action
    return None


def _is_a2ui_part(part: Part) -> bool:
    """Identify an A2UI data part by its standard MIME type."""
    return (
        part.WhichOneof("content") == "data"
        and MessageToDict(part.metadata).get("mimeType") == A2UI_MIME_TYPE
    )
