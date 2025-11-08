# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3200 - Module for testing select_ai agents
"""
import uuid

import pytest
import select_ai
from select_ai.agent import Agent, AgentAttributes

PYSAI_3200_AGENT_NAME = f"PYSAI_3200_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_3200_AGENT_DESCRIPTION = "PYSAI_3200_AGENT_DESCRIPTION"
PYSAI_3200_PROFILE_NAME = f"PYSAI_3200_PROFILE_{uuid.uuid4().hex.upper()}"


@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_3200_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def agent_attributes():
    agent_attributes = AgentAttributes(
        profile_name=PYSAI_3200_PROFILE_NAME,
        role="You are an AI Movie Analyst. "
        "Your can help answer a variety of questions related to movies. ",
        enable_human_tool=False,
    )
    return agent_attributes


@pytest.fixture(scope="module")
def agent(python_gen_ai_profile, agent_attributes):
    agent = Agent(
        agent_name=PYSAI_3200_AGENT_NAME,
        attributes=agent_attributes,
        description=PYSAI_3200_AGENT_DESCRIPTION,
    )
    agent.create(enabled=True, replace=True)
    yield agent
    agent.delete(force=True)


def test_3200(agent, agent_attributes):
    assert agent.agent_name == PYSAI_3200_AGENT_NAME
    assert agent.attributes == agent_attributes
    assert agent.description == PYSAI_3200_AGENT_DESCRIPTION


@pytest.mark.parametrize("agent_name_pattern", [None, "^PYSAI_3200_AGENT_"])
def test_3201(agent_name_pattern):
    if agent_name_pattern:
        agents = list(select_ai.agent.Agent.list(agent_name_pattern))
    else:
        agents = list(select_ai.agent.Agent.list())
    agent_names = set(agent.agent_name for agent in agents)
    agent_descriptions = set(agent.description for agent in agents)
    assert PYSAI_3200_AGENT_NAME in agent_names
    assert PYSAI_3200_AGENT_DESCRIPTION in agent_descriptions
