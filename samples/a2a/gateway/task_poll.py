# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Connect to a dynamic A2A gateway, then poll a database task."""

import time

from _common import call, connect, print_task_summary, send_prompt

PROMPT = "What were last month's sales by product category?"
TERMINAL_STATES = {"completed", "failed", "canceled", "rejected"}


context_id = connect(PROMPT)
task = send_prompt(PROMPT, context_id, blocking=False)
print(f"Task {task['id']}: {task['status']['state']}")

while task["status"]["state"] not in TERMINAL_STATES:
    time.sleep(1)
    task = call("tasks/get", {"id": task["id"]})
    print(f"Task {task['id']}: {task['status']['state']}")

if task["artifacts"][0]["name"] != "database-agent-result":
    raise RuntimeError(
        "Expected a database result, got " f"{task['artifacts'][0]['name']}"
    )
print_task_summary(task, include_task=False)
