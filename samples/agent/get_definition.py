# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/get_definition.py
#
# Create a temporary task and print its canonical PL/SQL definition.
# -----------------------------------------------------------------------------

import os
import uuid

import select_ai
from select_ai.agent import Task, TaskAttributes, get_definition

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

task = Task(
    task_name=f"SAMPLE_DEFINITION_TASK_{uuid.uuid4().hex.upper()}",
    attributes=TaskAttributes(
        instruction="Answer the user's question: {query}", tools=[]
    ),
)
task.create(replace=True)

try:
    print(get_definition("TASK", task.task_name))
finally:
    task.delete(force=True)
