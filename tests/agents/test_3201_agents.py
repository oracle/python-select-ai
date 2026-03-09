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
import logging
import pytest
import select_ai
import os
from select_ai.agent import Agent, AgentAttributes
from select_ai.errors import AgentNotFoundError
import oracledb

# Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3201_agents.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Force logging to file (pytest-proof)
root = logging.getLogger()
root.setLevel(logging.INFO)

for h in root.handlers[:]:
    root.removeHandler(h)

fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)

logger = logging.getLogger()


# -----------------------------------------------------------------------------
# Per-test logging
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def get_agent_status(agent_name):
    with select_ai.cursor() as cur:
        cur.execute("""
            SELECT status
            FROM USER_AI_AGENTS
            WHERE agent_name = :agent_name
        """, {"agent_name": agent_name})
        row = cur.fetchone()
        return row[0] if row else None

# -----------------------------------------------------------------------------
# Test constants
# -----------------------------------------------------------------------------

PYSAI_AGENT_NAME = f"PYSAI_3200_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_AGENT_DESC = "PYSAI_3200_AGENT_DESCRIPTION"
PYSAI_PROFILE_NAME = f"PYSAI_3200_PROFILE_{uuid.uuid4().hex.upper()}"

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    logger.info("Creating profile: %s", PYSAI_PROFILE_NAME)
    profile = select_ai.Profile(
        profile_name=PYSAI_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    profile.create(replace=True)
    yield profile
    logger.info("Deleting profile: %s", PYSAI_PROFILE_NAME)
    profile.delete(force=True)


@pytest.fixture(scope="module")
def agent_attributes():
    return AgentAttributes(
        profile_name=PYSAI_PROFILE_NAME,
        role="You are an AI Movie Analyst. You analyze movies.",
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
def agent(python_gen_ai_profile, agent_attributes):
    logger.info("Creating agent: %s", PYSAI_AGENT_NAME)
    agent = Agent(
        agent_name=PYSAI_AGENT_NAME,
        description=PYSAI_AGENT_DESC,
        attributes=agent_attributes,
    )
    agent.create(enabled=True, replace=True)
    yield agent
    logger.info("Deleting agent: %s", PYSAI_AGENT_NAME)
    agent.delete(force=True)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def expect_oracle_error(expected_code, fn):
    """
    Run fn and assert that expected Oracle/Agent error occurs.
    expected_code: "ORA-xxxxx" or "NOT_FOUND"
    """
    try:
        fn()
    except AgentNotFoundError as e:
        logger.info("Expected failure (NOT_FOUND): %s", e)
        assert expected_code == "NOT_FOUND"
    except oracledb.DatabaseError as e:
        msg = str(e)
        logger.info("Expected Oracle failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got {msg}"
    else:
        pytest.fail(f"Expected error {expected_code} did not occur")

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_3200_identity(agent, agent_attributes):
    logger.info("Verifying agent identity")
    logger.info("Agent name       : %s", agent.agent_name)
    logger.info("Agent description: %s", agent.description)
    logger.info("Agent attributes : %s", agent.attributes)
    assert agent.agent_name == PYSAI_AGENT_NAME
    assert agent.description == PYSAI_AGENT_DESC
    assert agent.attributes == agent_attributes


@pytest.mark.parametrize("pattern", [None, ".*", "^PYSAI_3200_AGENT_"])
def test_3201_list(pattern):
    logger.info("Listing agents with pattern: %s", pattern)
    agents = list(Agent.list() if pattern is None else Agent.list(pattern))
    names = sorted(a.agent_name for a in agents)
    logger.info("Agents found (sorted):")
    for name in names:
        logger.info("  - %s", name)

    assert PYSAI_AGENT_NAME in names


def test_3202_fetch(agent_attributes):
    logger.info("Fetching agent: %s", PYSAI_AGENT_NAME)
    a = Agent.fetch(PYSAI_AGENT_NAME)
    logger.info("Fetched agent name       : %s", a.agent_name)
    logger.info("Fetched agent description: %s", a.description)
    logger.info("Fetched agent attributes : %s", a.attributes)
    assert a.agent_name == PYSAI_AGENT_NAME
    assert a.attributes == agent_attributes
    assert a.description == PYSAI_AGENT_DESC


def test_3203_fetch_non_existing():
    name = f"PYSAI_NO_SUCH_AGENT_{uuid.uuid4().hex}"
    logger.info("Fetching non-existing agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))


def test_3204_disable_enable(agent):
    logger.info("Disabling agent: %s", agent.agent_name)
    agent.disable()

    status = get_agent_status(agent.agent_name)
    logger.info("Agent status after disable: %s", status)
    assert status == "DISABLED"

    logger.info("Enabling agent: %s", agent.agent_name)
    agent.enable()

    status = get_agent_status(agent.agent_name)
    logger.info("Agent status after enable: %s", status)
    assert status == "ENABLED"


def test_3205_set_attribute(agent):
    logger.info("Setting role attribute on agent: %s", agent.agent_name)
    agent.set_attribute("role", "You are a DB assistant")

    a = Agent.fetch(PYSAI_AGENT_NAME)
    logger.info("Updated role attribute: %s", a.attributes.role)

    assert "DB assistant" in a.attributes.role


def test_3206_set_attributes(agent):
    logger.info("Replacing agent attributes")

    new_attrs = AgentAttributes(
        profile_name=PYSAI_PROFILE_NAME,
        role="You are a cloud architect",
        enable_human_tool=True,
    )

    logger.info("New attributes: %s", new_attrs)
    agent.set_attributes(new_attrs)

    a = Agent.fetch(PYSAI_AGENT_NAME)
    logger.info("Fetched attributes after replace: %s", a.attributes)

    assert a.attributes == new_attrs


def test_3207_set_attribute_invalid_key(agent):
    logger.info("Setting invalid attribute key on agent: %s", agent.agent_name)
    expect_oracle_error("ORA-20050", lambda: agent.set_attribute("no_such_key", 123))

def test_3208_set_attribute_none(agent):
    logger.info("Setting attribute 'role' to None on agent: %s", agent.agent_name)
    expect_oracle_error("ORA-20050", lambda: agent.set_attribute("role", None))

def test_3209_set_attribute_empty(agent):
    logger.info("Setting attribute 'role' to empty string on agent: %s", agent.agent_name)
    expect_oracle_error("ORA-20050", lambda: agent.set_attribute("role", ""))

def test_3210_create_existing_without_replace(agent_attributes):
    logger.info("Create existing agent without replace should fail")
    a = Agent(
        agent_name=PYSAI_AGENT_NAME,
        description="X",
        attributes=agent_attributes,
    )
    expect_oracle_error("ORA-20050", lambda: a.create(replace=False))

def test_3211_delete_and_recreate(agent_attributes):
    name = f"PYSAI_RECREATE_{uuid.uuid4().hex}"
    logger.info("Create agent: %s", name)
    #Create agent
    a = Agent(name, attributes=agent_attributes)
    a.create()
    # Verify created
    fetched = Agent.fetch(name)
    logger.info("Agent created successfully: %s", fetched.agent_name)
    assert fetched.agent_name == name
    #Delete agent
    logger.info("Delete agent: %s", name)
    a.delete(force=True)
    # Verify deleted
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Agent deleted successfully: %s", name)
    #Recreate agent
    logger.info("Recreate agent: %s", name)
    a.create(replace=False)
    # Verify recreated
    fetched_recreated = Agent.fetch(name)
    logger.info("Agent recreated successfully: %s", fetched_recreated.agent_name)
    assert fetched_recreated.agent_name == name
    #Final cleanup
    logger.info("Cleanup agent: %s", name)
    a.delete(force=True)
    # Verify cleanup
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Final cleanup successful for agent: %s", name)


def test_3212_disable_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex}"
    logger.info("Creating agent: %s", name)
    a = Agent(name, attributes=agent_attributes)
    a.create()
    logger.info("Agent created successfully: %s", name)

    logger.info("Fetching agent to verify creation: %s", name)
    fetched = Agent.fetch(name)
    logger.info("Fetched agent: %s", fetched.agent_name)

    logger.info("Deleting agent: %s", name)
    a.delete(force=True)
    logger.info("Agent deleted, verifying deletion: %s", name)
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent no longer exists: %s", name)

    logger.info("Attempting to disable deleted agent: %s", name)
    expect_oracle_error("ORA-20050", lambda: a.disable())
    logger.info("Disable after delete confirmed error for agent: %s", name)


def test_3213_enable_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex}"
    logger.info("Creating agent: %s", name)
    a = Agent(name, attributes=agent_attributes)
    a.create()
    logger.info("Agent created successfully: %s", name)

    logger.info("Fetching agent to verify creation: %s", name)
    fetched = Agent.fetch(name)
    logger.info("Fetched agent: %s", fetched.agent_name)

    logger.info("Deleting agent: %s", name)
    a.delete(force=True)
    logger.info("Agent deleted, verifying deletion: %s", name)
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent no longer exists: %s", name)

    logger.info("Attempting to enable deleted agent: %s", name)
    expect_oracle_error("ORA-20050", lambda: a.enable())
    logger.info("Enable after delete confirmed error for agent: %s", name)


def test_3214_set_attribute_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex}"
    logger.info("Creating agent: %s", name)
    a = Agent(name, attributes=agent_attributes)
    a.create()
    logger.info("Agent created successfully: %s", name)

    logger.info("Fetching agent to verify creation: %s", name)
    fetched = Agent.fetch(name)
    logger.info("Fetched agent: %s", fetched.agent_name)

    logger.info("Deleting agent: %s", name)
    a.delete(force=True)
    logger.info("Agent deleted, verifying deletion: %s", name)
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent no longer exists: %s", name)

    logger.info("Attempting to set attribute on deleted agent: %s", name)
    expect_oracle_error("ORA-20050", lambda: a.set_attribute("role", "X"))
    logger.info("Set attribute after delete confirmed error for agent: %s", name)


def test_3215_double_delete(agent_attributes):
    name = f"PYSAI_TMP_DOUBLE_DEL_{uuid.uuid4().hex}"
    logger.info("Creating agent: %s", name)
    a = Agent(name, attributes=agent_attributes)
    a.create()
    logger.info("Agent created successfully: %s", name)

    logger.info("Fetching agent to verify creation: %s", name)
    fetched = Agent.fetch(name)
    logger.info("Fetched agent: %s", fetched.agent_name)

    logger.info("Deleting agent first time: %s", name)
    a.delete(force=True)
    logger.info("First delete done, verifying deletion: %s", name)
    logger.info("Attempting fetch after first delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent no longer exists: %s", name)

    logger.info("Deleting agent second time (should not fail): %s", name)
    a.delete(force=True)
    logger.info("Second delete completed, verifying still deleted: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent still does not exist after double delete: %s", name)


def test_3216_fetch_after_delete(agent_attributes):
    name = f"PYSAI_TMP_FETCH_DEL_{uuid.uuid4().hex}"
    logger.info("Creating agent: %s", name)
    a = Agent(name, attributes=agent_attributes)
    a.create()
    logger.info("Agent created successfully: %s", name)

    logger.info("Fetching agent to verify creation: %s", name)
    fetched = Agent.fetch(name)
    logger.info("Fetched agent: %s", fetched.agent_name)

    logger.info("Deleting agent: %s", name)
    a.delete(force=True)
    logger.info("Agent deleted, verifying deletion: %s", name)
    logger.info("Attempting fetch after delete for agent: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Agent.fetch(name))
    logger.info("Confirmed agent no longer exists: %s", name)


def test_3217_list_all_non_empty():
    logger.info("Listing all agents")
    agents = list(Agent.list())
    names = sorted(a.agent_name for a in agents)
    logger.info("Total agents found: %d", len(names))
    logger.info("Agent names:")
    for name in names:
        logger.info("  - %s", name)
    assert len(names) > 0
