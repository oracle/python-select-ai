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
