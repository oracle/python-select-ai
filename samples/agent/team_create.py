# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# team_create.py
#
# Create a team for movie analyst and run it
# -----------------------------------------------------------------------------

import os
import uuid

import select_ai
from select_ai.agent import (
    Team,
    TeamAttributes,
)

conversation_id = str(uuid.uuid4())

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

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
        prompt="Could you list the movies in the database?",
        params={"conversation_id": conversation_id},
    )
)
