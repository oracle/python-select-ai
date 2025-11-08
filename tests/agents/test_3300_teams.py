# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3300 - Module for testing select_ai agent teams
"""

import uuid

import pytest
import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
)

PYSAI_3300_AGENT_NAME = f"PYSAI_3300_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_3300_AGENT_DESCRIPTION = "PYSAI_3300_AGENT_DESCRIPTION"
PYSAI_3300_PROFILE_NAME = f"PYSAI_3300_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TASK_NAME = f"PYSAI_3300_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TASK_DESCRIPTION = "PYSAI_3100_SQL_TASK_DESCRIPTION"
PYSAI_3300_TEAM_NAME = f"PYSAI_3300_TEAM_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TEAM_DESCRIPTION = "PYSAI_3300_TEAM_DESCRIPTION"


@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_3300_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def task_attributes():
    return TaskAttributes(
        instruction="Help the user with their request about movies. "
        "User question: {query}. ",
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
def task(task_attributes):
    task = Task(
        task_name=PYSAI_3300_TASK_NAME,
        description=PYSAI_3300_TASK_DESCRIPTION,
        attributes=task_attributes,
    )
    task.create()
    yield task
    task.delete(force=True)


@pytest.fixture(scope="module")
def agent(python_gen_ai_profile):
    agent = Agent(
        agent_name=PYSAI_3300_AGENT_NAME,
        description=PYSAI_3300_AGENT_DESCRIPTION,
        attributes=AgentAttributes(
            profile_name=PYSAI_3300_PROFILE_NAME,
            role="You are an AI Movie Analyst. "
            "Your can help answer a variety of questions related to movies. ",
            enable_human_tool=False,
        ),
    )
    agent.create(enabled=True, replace=True)
    yield agent
    agent.delete(force=True)


@pytest.fixture(scope="module")
def team_attributes(agent, task):
    return TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )


@pytest.fixture(scope="module")
def team(team_attributes):
    team = Team(
        team_name=PYSAI_3300_TEAM_NAME,
        description=PYSAI_3300_TEAM_DESCRIPTION,
        attributes=team_attributes,
    )
    team.create()
    yield team
    team.delete(force=True)


def test_3300(team, team_attributes):
    assert team.team_name == PYSAI_3300_TEAM_NAME
    assert team.description == PYSAI_3300_TEAM_DESCRIPTION
    assert team.attributes == team_attributes


@pytest.mark.parametrize("team_name_pattern", [None, "^PYSAI_3300_TEAM_"])
def test_3301(team_name_pattern):
    if team_name_pattern:
        teams = list(Team.list(team_name_pattern))
    else:
        teams = list(Team.list())
    team_names = set(team.team_name for team in teams)
    team_descriptions = set(team.description for team in teams)
    assert PYSAI_3300_TEAM_NAME in team_names
    assert PYSAI_3300_TEAM_DESCRIPTION in team_descriptions


def test_3302(team_attributes):
    team = Team.fetch(team_name=PYSAI_3300_TEAM_NAME)
    assert team.team_name == PYSAI_3300_TEAM_NAME
    assert team.description == PYSAI_3300_TEAM_DESCRIPTION
    assert team.attributes == team_attributes


def test_3303(team):
    response = team.run(
        prompt="In the movie Titanic, was there enough space for Jack ? ",
        params={"conversation_id": str(uuid.uuid4())},
    )
    assert isinstance(response, str)
    assert len(response) > 0
