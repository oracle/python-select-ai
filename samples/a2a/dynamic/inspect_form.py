# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Request and print the dynamic A2UI database connection form."""

import json

from _common import request_connection_form

task, fields = request_connection_form("Show the database connection form.")
print(f"Context: {task['contextId']}")
print("Requested fields: " + ", ".join(fields))
print(json.dumps(task["artifacts"][0], indent=2))
