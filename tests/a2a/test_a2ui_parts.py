# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json

import pytest
from google.protobuf.json_format import MessageToDict

pytest.importorskip("a2a")

from select_ai.agent.a2a.server import _message_parts


def test_a2a_message_parts_are_forwarded_with_metadata():
    result = json.dumps(
        {
            "kind": "message",
            "parts": [
                {"kind": "text", "text": "A2UI visualization ready."},
                {
                    "kind": "data",
                    "data": {
                        "version": "v0.9",
                        "createSurface": {"surfaceId": "smoke-test"},
                    },
                    "metadata": {"mimeType": "application/json+a2ui"},
                },
            ],
        }
    )

    parts = _message_parts(result)

    assert [
        MessageToDict(part, preserving_proto_field_name=True) for part in parts
    ] == [
        {"text": "A2UI visualization ready."},
        {
            "data": {
                "version": "v0.9",
                "createSurface": {"surfaceId": "smoke-test"},
            },
            "metadata": {"mimeType": "application/json+a2ui"},
        },
    ]


def test_a2a_text_message_is_forwarded():
    result = json.dumps(
        {
            "kind": "message",
            "parts": [{"kind": "text", "text": "ordinary response"}],
        }
    )

    parts = _message_parts(result)

    assert [
        MessageToDict(part, preserving_proto_field_name=True) for part in parts
    ] == [{"text": "ordinary response"}]
