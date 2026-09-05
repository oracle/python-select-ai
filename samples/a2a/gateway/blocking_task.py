# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Connect to a dynamic A2A gateway, then send a blocking database request."""

from _common import connect, print_task_summary, send_prompt

PROMPT = "What were last month's sales by product category?"


context_id = connect(PROMPT)
task = send_prompt(PROMPT, context_id)
if task["artifacts"][0]["name"] != "database-agent-result":
    raise RuntimeError(
        "Expected a database result, got " f"{task['artifacts'][0]['name']}"
    )
print_task_summary(task)
