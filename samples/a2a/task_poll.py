# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Start a non-blocking A2A task, then poll until it completes."""

import json
import time
import uuid
from urllib.request import Request, urlopen

ENDPOINT = "http://127.0.0.1:8000/a2a/jsonrpc/"
PROMPT = "What were last month's sales by product category?"
TERMINAL_STATES = {"completed", "failed", "canceled", "rejected"}


def call(method, params):
    """Make one A2A v0.3 JSON-RPC call."""
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


# blocking=False returns immediately with a Task. Database work continues on
# the server while this client polls tasks/get.
task = call(
    "message/send",
    {
        "message": {
            "messageId": str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": PROMPT}],
        },
        "configuration": {"blocking": False},
    },
)

task_id = task["id"]
print(f"Task {task_id}: {task['status']['state']}")

while task["status"]["state"] not in TERMINAL_STATES:
    time.sleep(1)
    task = call("tasks/get", {"id": task_id})
    print(f"Task {task_id}: {task['status']['state']}")

print(json.dumps(task, indent=2))
