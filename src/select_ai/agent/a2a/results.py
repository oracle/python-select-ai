# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Translate serialized Select AI team results into A2A response artifacts."""

from __future__ import annotations

import json

from a2a.helpers import new_data_part, new_text_part
from a2a.server.tasks import TaskUpdater
from google.protobuf.json_format import ParseDict


def message_parts(result: str | None):
    """Convert a serialized A2A message into its constituent parts."""
    if not result:
        return None
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    serialized_parts = payload.get("parts")
    if payload.get("kind") != "message" or not isinstance(
        serialized_parts,
        list,
    ):
        return None
    parts = []
    for part in serialized_parts:
        if not isinstance(part, dict):
            return None
        if part.get("kind") == "text" and isinstance(part.get("text"), str):
            parts.append(new_text_part(part["text"]))
        elif part.get("kind") == "data" and "data" in part:
            output_part = new_data_part(part["data"])
            if isinstance(part.get("metadata"), dict):
                ParseDict(part["metadata"], output_part.metadata)
            parts.append(output_part)
        else:
            # Avoid silently discarding an unsupported part type.
            return None
    return parts or None


async def add_team_result(updater: TaskUpdater, result: str | None) -> None:
    """Attach a raw team result as the completed database-result artifact."""
    await updater.add_artifact(
        parts=message_parts(result) or [new_text_part(result or "")],
        name="database-agent-result",
        last_chunk=True,
    )
