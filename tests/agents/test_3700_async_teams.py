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
    AsyncTaskHistory,
    AsyncTeam,
    AsyncTeamHistory,
    AsyncTool,
    AsyncToolHistory,
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
PYSAI_3700_FUNCTION_NAME = f"PYSAI_3700_FUNCTION_{uuid.uuid4().hex.upper()}"
PYSAI_3700_TOOL_NAME = f"PYSAI_3700_TOOL_{uuid.uuid4().hex.upper()}"


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
async def history_tool():
    async with select_ai.async_cursor() as cr:
        await cr.execute(
            f"""
            CREATE OR REPLACE FUNCTION {PYSAI_3700_FUNCTION_NAME}
            RETURN VARCHAR2
            IS
            BEGIN
                RETURN '{{"message":"async history test complete"}}';
            END;
            """
        )

    tool = await AsyncTool.create_pl_sql_tool(
        tool_name=PYSAI_3700_TOOL_NAME,
        function=PYSAI_3700_FUNCTION_NAME,
        description="Returns JSON with the async history test result",
    )
    yield tool
    await tool.delete(force=True)
    async with select_ai.async_cursor() as cr:
        await cr.execute(f"DROP FUNCTION {PYSAI_3700_FUNCTION_NAME}")


@pytest.fixture(scope="module")
async def task_attributes(history_tool):
    return TaskAttributes(
        instruction="You must call the available tool exactly once, then "
        "answer the user's question using its result. User question: {query}.",
        tools=[history_tool.tool_name],
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
    conversation = select_ai.AsyncConversation(
        attributes=select_ai.ConversationAttributes(
            title="Async agent team test",
            description="Conversation for async team run test",
        )
    )
    await conversation.create()
    try:
        response = await team.run(
            prompt="In the movie Titanic, was there enough space for Jack ? ",
            params={"conversation_id": conversation.conversation_id},
        )
        assert isinstance(response, str)
        assert len(response) > 0
    finally:
        await conversation.delete(force=True)


async def test_3304_async_team_and_task_history(team):
    """Run a team and retrieve its generated history rows asynchronously."""
    conversation = select_ai.AsyncConversation(
        attributes=select_ai.ConversationAttributes(
            title="Async agent history test",
            description="Conversation for async agent history test",
        )
    )
    await conversation.create()
    try:
        response = await team.run(
            prompt="Reply with one sentence about the movie Titanic.",
            params={"conversation_id": conversation.conversation_id},
        )
        assert isinstance(response, str)
        assert response

        team_runs = [
            run
            async for run in AsyncTeamHistory.list(
                team_name=team.team_name,
                limit=1,
            )
        ]
        assert len(team_runs) == 1
        assert team_runs[0].team_name == team.team_name
        assert team_runs[0].team_exec_id
        assert team_runs[0].conversation_id == conversation.conversation_id

        task_runs = [
            run
            async for run in AsyncTaskHistory.list(
                team_exec_id=team_runs[0].team_exec_id,
                limit=1,
            )
        ]
        assert len(task_runs) == 1
        assert task_runs[0].team_name == team.team_name
        assert task_runs[0].task_name == PYSAI_3700_TASK_NAME

        tool_runs = [
            run
            async for run in AsyncToolHistory.list(
                tool_name=PYSAI_3700_TOOL_NAME,
                team_exec_id=team_runs[0].team_exec_id,
                limit=1,
            )
        ]
        assert len(tool_runs) == 1
        assert tool_runs[0].tool_name == PYSAI_3700_TOOL_NAME
        assert tool_runs[0].invocation_id
        assert tool_runs[0].output == {
            "status": "success",
            "result": '\'{"message":"async history test complete"}\'',
        }
    finally:
        await conversation.delete(force=True)
