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
    TaskHistory,
    Team,
    TeamAttributes,
    TeamHistory,
    Tool,
    ToolHistory,
)

PYSAI_3300_AGENT_NAME = f"PYSAI_3300_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_3300_AGENT_DESCRIPTION = "PYSAI_3300_AGENT_DESCRIPTION"
PYSAI_3300_PROFILE_NAME = f"PYSAI_3300_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TASK_NAME = f"PYSAI_3300_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TASK_DESCRIPTION = "PYSAI_3100_SQL_TASK_DESCRIPTION"
PYSAI_3300_TEAM_NAME = f"PYSAI_3300_TEAM_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TEAM_DESCRIPTION = "PYSAI_3300_TEAM_DESCRIPTION"
PYSAI_3300_FUNCTION_NAME = f"PYSAI_3300_FUNCTION_{uuid.uuid4().hex.upper()}"
PYSAI_3300_TOOL_NAME = f"PYSAI_3300_TOOL_{uuid.uuid4().hex.upper()}"


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
def history_tool():
    with select_ai.cursor() as cr:
        cr.execute(
            f"""
            CREATE OR REPLACE FUNCTION {PYSAI_3300_FUNCTION_NAME}
            RETURN VARCHAR2
            IS
            BEGIN
                RETURN '{"message":"history test complete"}';
            END;
            """
        )

    tool = Tool.create_pl_sql_tool(
        tool_name=PYSAI_3300_TOOL_NAME,
        function=PYSAI_3300_FUNCTION_NAME,
        description="Returns JSON with the history test result",
    )
    yield tool
    tool.delete(force=True)
    with select_ai.cursor() as cr:
        cr.execute(f"DROP FUNCTION {PYSAI_3300_FUNCTION_NAME}")


@pytest.fixture(scope="module")
def task_attributes(history_tool):
    return TaskAttributes(
        instruction="You must call the available tool exactly once, then "
        "answer the user's question using its result. User question: {query}.",
        tools=[history_tool.tool_name],
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
    conversation = select_ai.Conversation(
        attributes=select_ai.ConversationAttributes(
            title="Agent team test",
            description="Conversation for team run test",
        )
    )
    conversation.create()
    try:
        response = team.run(
            prompt="In the movie Titanic, was there enough space for Jack ? ",
            params={"conversation_id": conversation.conversation_id},
        )
        assert isinstance(response, str)
        assert len(response) > 0
    finally:
        conversation.delete(force=True)


def test_3304_team_and_task_history(team):
    """Run a team and retrieve its generated team and task history rows."""
    conversation = select_ai.Conversation(
        attributes=select_ai.ConversationAttributes(
            title="Agent history test",
            description="Conversation for agent history test",
        )
    )
    conversation.create()
    try:
        response = team.run(
            prompt="Reply with one sentence about the movie Titanic.",
            params={"conversation_id": conversation.conversation_id},
        )
        assert isinstance(response, str)
        assert response

        team_runs = list(TeamHistory.list(team_name=team.team_name, limit=1))
        assert len(team_runs) == 1
        assert team_runs[0].team_name == team.team_name
        assert team_runs[0].team_exec_id
        assert team_runs[0].conversation_id == conversation.conversation_id

        task_runs = list(
            TaskHistory.list(team_exec_id=team_runs[0].team_exec_id, limit=1)
        )
        assert len(task_runs) == 1
        assert task_runs[0].team_name == team.team_name
        assert task_runs[0].task_name == PYSAI_3300_TASK_NAME

        tool_runs = list(
            ToolHistory.list(
                tool_name=PYSAI_3300_TOOL_NAME,
                team_exec_id=team_runs[0].team_exec_id,
                limit=1,
            )
        )
        assert len(tool_runs) == 1
        assert tool_runs[0].tool_name == PYSAI_3300_TOOL_NAME
        assert tool_runs[0].invocation_id
        assert tool_runs[0].output == {"message": "history test complete"}
    finally:
        conversation.delete(force=True)
