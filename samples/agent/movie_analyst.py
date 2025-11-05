# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# movie_analyst.py
#
# Demonstrates movie analyst AI agent
# -----------------------------------------------------------------------------

import os
import uuid

import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
)

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

# Agent
agent = Agent(
    agent_name="MOVIE_ANALYST",
    attributes=AgentAttributes(
        profile_name="oci_ai_profile",
        role="You are an AI Movie Analyst. "
        "Your can help answer a variety of questions related to movies. ",
        enable_human_tool=False,
    ),
)
agent.create(enabled=True, replace=True)
print("Create Agent", agent)

# Task
task = Task(
    task_name="ANALYZE_MOVIE_TASK",
    description="Movie task involving a human",
    attributes=TaskAttributes(
        instruction="Help the user with their request about movies. "
        "User question: {query}",
        enable_human_tool=False,
    ),
)
task.create(replace=True)
print("Created Task", task)

# Team
team = Team(
    team_name="MOVIE_AGENT_TEAM",
    attributes=TeamAttributes(
        agents=[{"name": "MOVIE_ANALYST", "task": "ANALYZE_MOVIE_TASK"}],
        process="sequential",
    ),
)
team.create(enabled=True, replace=True)
print(
    team.run(
        prompt="In the movie Titanic, was there enough space for Jack ? ",
        params={"conversation_id": str(uuid.uuid4())},
    )
)
