# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Send a blocking A2A request and receive its completed task."""

import json
import uuid
from urllib.request import Request, urlopen

ENDPOINT = "http://127.0.0.1:8000/a2a/jsonrpc/"
PROMPT = "What were last month's sales by product category?"


# There is intentionally no "configuration": {"blocking": false} here.
# Omitting it is blocking by default, so this call waits for the database work
# to finish before the server returns the Task.
request = Request(
    ENDPOINT,
    data=json.dumps(
        {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"kind": "text", "text": PROMPT}],
                }
            },
        }
    ).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urlopen(request) as response:  # noqa: S310
    body = json.load(response)
if "error" in body:
    raise RuntimeError(body["error"])

task = body["result"]
print(f"Task {task['id']}: {task['status']['state']}")
print(json.dumps(task, indent=2))
