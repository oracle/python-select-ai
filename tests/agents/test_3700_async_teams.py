# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3700 - Module for testing select_ai agent async teams
"""

import uuid

import pytest
import select_ai
from select_ai.agent import (
    AgentAttributes,
    AsyncAgent,
    AsyncTask,
    AsyncTeam,
    TaskAttributes,
    TeamAttributes,
)

PYSAI_3700_AGENT_NAME = f"PYSAI_3700_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_3700_AGENT_DESCRIPTION = "PYSAI_3700_AGENT_DESCRIPTION"
PYSAI_3700_PROFILE_NAME = f"PYSAI_3700_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_3700_TASK_NAME = f"PYSAI_3700_{uuid.uuid4().hex.upper()}"
PYSAI_3700_TASK_DESCRIPTION = "PYSAI_3100_SQL_TASK_DESCRIPTION"
PYSAI_3700_TEAM_NAME = f"PYSAI_3700_TEAM_{uuid.uuid4().hex.upper()}"
PYSAI_3700_TEAM_DESCRIPTION = "PYSAI_3700_TEAM_DESCRIPTION"


@pytest.fixture(scope="module")
async def python_gen_ai_profile(profile_attributes):
    profile = await select_ai.AsyncProfile(
        profile_name=PYSAI_3700_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    await profile.delete(force=True)


@pytest.fixture(scope="module")
def task_attributes():
    return TaskAttributes(
        instruction="Help the user with their request about movies. "
        "User question: {query}. ",
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
async def task(task_attributes):
    task = AsyncTask(
        task_name=PYSAI_3700_TASK_NAME,
        description=PYSAI_3700_TASK_DESCRIPTION,
        attributes=task_attributes,
    )
    await task.create()
    yield task
    await task.delete(force=True)


@pytest.fixture(scope="module")
async def agent(python_gen_ai_profile):
    agent = AsyncAgent(
        agent_name=PYSAI_3700_AGENT_NAME,
        description=PYSAI_3700_AGENT_DESCRIPTION,
        attributes=AgentAttributes(
            profile_name=PYSAI_3700_PROFILE_NAME,
            role="You are an AI Movie Analyst. "
            "Your can help answer a variety of questions related to movies. ",
            enable_human_tool=False,
        ),
    )
    await agent.create(enabled=True, replace=True)
    yield agent
    await agent.delete(force=True)


@pytest.fixture(scope="module")
def team_attributes(agent, task):
    return TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )


@pytest.fixture(scope="module")
async def team(team_attributes):
    team = AsyncTeam(
        team_name=PYSAI_3700_TEAM_NAME,
        description=PYSAI_3700_TEAM_DESCRIPTION,
        attributes=team_attributes,
    )
    await team.create()
    yield team
    await team.delete(force=True)


def test_3300(team, team_attributes):
    assert team.team_name == PYSAI_3700_TEAM_NAME
    assert team.description == PYSAI_3700_TEAM_DESCRIPTION
    assert team.attributes == team_attributes


@pytest.mark.parametrize("team_name_pattern", [None, "^PYSAI_3700_TEAM_"])
async def test_3301(team_name_pattern):
    if team_name_pattern:
        teams = [team async for team in AsyncTeam.list(team_name_pattern)]
    else:
        teams = [team async for team in select_ai.agent.AsyncTeam.list()]
    team_names = set(team.team_name for team in teams)
    team_descriptions = set(team.description for team in teams)
    assert PYSAI_3700_TEAM_NAME in team_names
    assert PYSAI_3700_TEAM_DESCRIPTION in team_descriptions


async def test_3302(team_attributes):
    team = await AsyncTeam.fetch(team_name=PYSAI_3700_TEAM_NAME)
    assert team.team_name == PYSAI_3700_TEAM_NAME
    assert team.description == PYSAI_3700_TEAM_DESCRIPTION
    assert team.attributes == team_attributes


async def test_3303(team):
    response = await team.run(
        prompt="In the movie Titanic, was there enough space for Jack ? ",
        params={"conversation_id": str(uuid.uuid4())},
    )
    assert isinstance(response, str)
    assert len(response) > 0
