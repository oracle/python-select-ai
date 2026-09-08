# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Small A2A v0.3 client helpers for the dynamic gateway samples."""

import json
import os
import uuid
from urllib.request import Request, urlopen

ENDPOINT = os.environ.get(
    "SELECT_AI_A2A_GATEWAY_ENDPOINT",
    "http://127.0.0.1:8000/a2a/jsonrpc/",
)
TEAM_NAME = os.environ.get("SELECT_AI_A2A_TEAM", "ORACLE_AI_DATABASE_AGENT")


def call(method: str, params: dict) -> dict:
    """Make one A2A v0.3 JSON-RPC call and return its result."""
    request = Request(
        ENDPOINT,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": method,
                "params": params,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:  # noqa: S310
        body = json.load(response)
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


def _message(text: str, context_id: str | None = None) -> dict:
    message = {
        "messageId": str(uuid.uuid4()),
        "role": "user",
        "parts": [{"kind": "text", "text": text}],
    }
    if context_id:
        message["contextId"] = context_id
    return message


def connect(prompt: str) -> str:
    """Bootstrap one gateway session and return its context ID."""
    form_task = call("message/send", {"message": _message(prompt)})
    if form_task["artifacts"][0]["name"] != "database-connection-form":
        raise RuntimeError(
            "Expected database-connection-form, got "
            f"{form_task['artifacts'][0].get('name')}"
        )

    context_id = form_task["contextId"]
    connection_task = call(
        "message/send",
        {
            "message": {
                "messageId": str(uuid.uuid4()),
                "contextId": context_id,
                "taskId": form_task["id"],
                "role": "user",
                "parts": [
                    {
                        "kind": "data",
                        "data": {
                            "version": "v0.9",
                            "action": {
                                "name": "submit_database_connection",
                                "context": {
                                    "dsn": os.environ[
                                        "SELECT_AI_DB_CONNECT_STRING"
                                    ],
                                    "username": os.environ["SELECT_AI_USER"],
                                    "password": os.environ[
                                        "SELECT_AI_PASSWORD"
                                    ],
                                    "team_name": TEAM_NAME,
                                },
                            },
                        },
                        "metadata": {"mimeType": "application/json+a2ui"},
                    }
                ],
            }
        },
    )
    artifact = connection_task["artifacts"][0]
    if artifact["name"] != "database-session":
        raise RuntimeError(f"Database connection failed: {artifact['name']}")
    return context_id


def send_prompt(
    prompt: str,
    context_id: str,
    blocking: bool | None = None,
) -> dict:
    """Send a normal database prompt through an existing gateway session."""
    params = {"message": _message(prompt, context_id)}
    if blocking is False:
        params["configuration"] = {"blocking": False}
    return call("message/send", params)


def print_task_summary(task: dict, *, include_task: bool = True) -> None:
    """Print a useful result without dumping connection-form internals."""
    artifact = (task.get("artifacts") or [{}])[0]
    parts = artifact.get("parts") or [{}]
    if include_task:
        print(f"Task {task['id']}: {task['status']['state']}")
    print(f"Artifact: {artifact.get('name')}")
    for part in parts:
        if "text" in part:
            print(part["text"])
