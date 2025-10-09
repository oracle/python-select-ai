# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# tool_create_human.py
#
# Create a vector index for Retrieval Augmented Generation (RAG)
# -----------------------------------------------------------------------------

import os

import select_ai
import select_ai.agent

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

attributes = select_ai.agent.ToolAttributes(
    tool_params=select_ai.agent.HumanToolParams()
)

human_tool = select_ai.agent.Tool(
    attributes=attributes,
    tool_name="Human",
    description="My Select AI agent human tool",
)

human_tool.create()
