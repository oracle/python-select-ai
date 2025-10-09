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

# Agent
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
