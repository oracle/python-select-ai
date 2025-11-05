# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent_create.py
#
# Create an agent to answer any movie related questions
# -----------------------------------------------------------------------------

import os

import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
)

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai.connect(user=user, password=password, dsn=dsn)
agent_attributes = AgentAttributes(
    profile_name="LLAMA_4_MAVERICK",
    role="You are an AI Movie Analyst. "
    "Your can help answer a variety of questions related to movies. ",
    enable_human_tool=False,
)
agent = Agent(
    agent_name="MOVIE_ANALYST",
    attributes=agent_attributes,
)
agent.create(enabled=True, replace=True)
print("Created Agent:", agent)
