# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Shared A2UI protocol declarations for Select AI A2A agents."""

from a2a.types import AgentExtension
from google.protobuf.json_format import ParseDict
from google.protobuf.struct_pb2 import Struct

from select_ai.agent.a2a.forms import _CATALOG

A2UI_EXTENSION_URI = "https://a2ui.org/a2a-extension/a2ui/v0.9"
A2UI_MIME_TYPE = "application/json+a2ui"


def a2ui_extension() -> AgentExtension:
    """Return the A2UI v0.9 capability used by Gemini Enterprise."""
    params = ParseDict(
        {
            "acceptsInlineCatalogs": True,
            "supportedCatalogIds": [_CATALOG],
        },
        Struct(),
    )
    return AgentExtension(
        uri=A2UI_EXTENSION_URI,
        description="Provides agent driven UI using the A2UI JSON format.",
        params=params,
    )
