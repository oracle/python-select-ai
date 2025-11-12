# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# movie_analyst.py
#
# Demonstrates web search AI agent using OpenAI search
# -----------------------------------------------------------------------------

import os

import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
    Tool,
)

OPEN_AI_CREDENTIAL_NAME = "OPENAI_CRED"
OPEN_AI_PROFILE_NAME = "OPENAI_PROFILE"
SELECT_AI_AGENT_NAME = "WEB_SEARCH_AGENT"
SELECT_AI_TASK_NAME = "WEB_SEARCH_TASK"
SELECT_AI_TOOL_NAME = "WEB_SEARCH_TOOL"
SELECT_AI_TEAM_NAME = "WEB_SEARCH_TEAM"

USER_QUERIES = {
    "d917b055-e8a1-463a-a489-d4328a7b2210": "What are the key features for the product highlighted at "
    "this URL https://www.oracle.com/artificial-intelligence/database-machine-learning",
    "c2e3ff20-f56d-40e7-987c-cc72740c75a5": "What is the main topic at this URL https://www.oracle.com/artificial-intelligence/database-machine-learning",
    "25e23a25-07b9-4ed7-be11-f7e5e445d286": "What is the main topic at this URL https://openai.com",
}

# connect
user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
select_ai.connect(user=user, password=password, dsn=dsn)

# Create Open AI credential
select_ai.create_credential(
    credential={
        "credential_name": OPEN_AI_CREDENTIAL_NAME,
        "username": "OPENAI",
        "password": os.getenv("OPEN_AI_API_KEY"),
    },
    replace=True,
)
print("Created credential: ", OPEN_AI_CREDENTIAL_NAME)

# # Create Open AI Profile
profile = select_ai.Profile(
    profile_name=OPEN_AI_PROFILE_NAME,
    attributes=select_ai.ProfileAttributes(
        credential_name=OPEN_AI_CREDENTIAL_NAME,
        provider=select_ai.OpenAIProvider(model="gpt-4.1"),
    ),
    description="My Open AI Profile",
    replace=True,
)
print("Created profile: ", OPEN_AI_PROFILE_NAME)

# Create an AI Agent team
team = Team(
    team_name=SELECT_AI_TEAM_NAME,
    attributes=TeamAttributes(
        agents=[{"name": SELECT_AI_AGENT_NAME, "task": SELECT_AI_TASK_NAME}]
    ),
)
team.create(replace=True)

# Agent
agent = Agent(
    agent_name=SELECT_AI_AGENT_NAME,
    attributes=AgentAttributes(
        profile_name=OPEN_AI_PROFILE_NAME,
        enable_human_tool=False,
        role="You are a specialized web search agent that can access web page "
        "contents and respond to questions based on its content.",
    ),
)
agent.create(replace=True)

# Task
task = Task(
    task_name=SELECT_AI_TASK_NAME,
    attributes=TaskAttributes(
        instruction="Answer the user question about the provided URL:{query}",
        enable_human_tool=False,
        tools=[SELECT_AI_TOOL_NAME],
    ),
)
task.create(replace=True)

# Tool
web_search_tool = Tool.create_websearch_tool(
    tool_name=SELECT_AI_TOOL_NAME,
    credential_name=OPEN_AI_CREDENTIAL_NAME,
    description="Web Search Tool using OpenAI",
    replace=True,
)
print("Created tool: ", SELECT_AI_TOOL_NAME)

# Run the Agent Team
for conversation_id, prompt in USER_QUERIES.items():
    response = team.run(
        prompt=prompt, params={"conversation_id": conversation_id}
    )
    print(response)
