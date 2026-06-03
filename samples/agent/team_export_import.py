# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# team_export_import.py
#
# Export a team specification and import it as a new team.
# -----------------------------------------------------------------------------

import json
import os

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
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "LLAMA_4_MAVERICK")

select_ai.connect(user=user, password=password, dsn=dsn)

task = Task(
    task_name="EXPORT_IMPORT_MOVIE_TASK",
    description="Task used by the team export/import sample",
    attributes=TaskAttributes(
        instruction="Help the user with movie questions. Question: {query}",
        tools=[],
        enable_human_tool=False,
    ),
)
task.create(replace=True)

agent = Agent(
    agent_name="EXPORT_IMPORT_MOVIE_ANALYST",
    description="Agent used by the team export/import sample",
    attributes=AgentAttributes(
        profile_name=profile_name,
        role="You are an AI Movie Analyst.",
        enable_human_tool=False,
    ),
)
agent.create(enabled=True, replace=True)

source_team = Team(
    team_name="EXPORT_IMPORT_MOVIE_TEAM",
    attributes=TeamAttributes(
        agents=[
            {
                "name": agent.agent_name,
                "task": task.task_name,
            }
        ],
        process="sequential",
    ),
)
source_team.create(enabled=True, replace=True)

specification = json.loads(source_team.export())
print("Exported specification:")
print(json.dumps(specification, indent=2))

specification["name"] = "IMPORTED_MOVIE_ANALYST"
specification["task"]["task_name"] = "IMPORTED_ANALYZE_MOVIE_TASK"

Team.import_team(
    profile_name=profile_name,
    team_name="IMPORTED_MOVIE_AGENT_TEAM",
    specification=specification,
    force=True,
)

team = Team.fetch("IMPORTED_MOVIE_AGENT_TEAM")
print("Imported team:", team)
