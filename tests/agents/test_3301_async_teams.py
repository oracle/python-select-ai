# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3301 - Async contract, regression and corner-case tests for select_ai.agent.AsyncTeam
"""

import logging
import os
import uuid

import oracledb
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
from select_ai.errors import AgentTeamNotFoundError

pytestmark = pytest.mark.anyio

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_DIR = os.path.join(PROJECT_ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "tkex_test_3301_async_teams.log")

root = logging.getLogger()
root.setLevel(logging.INFO)
for h in root.handlers[:]:
    root.removeHandler(h)

fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# Per-test logging + async connection
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@pytest.fixture(scope="module", autouse=True)
async def async_connect(test_env):
    logger.info("Opening async database connection")
    await select_ai.async_connect(**test_env.connect_params())
    yield
    logger.info("Closing async database connection")
    await select_ai.async_disconnect()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

async def expect_async_error(expected_code, coro_fn):
    """
    expected_code:
      - "NOT_FOUND"
      - "ORA-20053"
      - "ORA-xxxxx"
    """
    try:
        await coro_fn()
    except AgentTeamNotFoundError as exc:
        logger.info("Expected failure (NOT_FOUND): %s", exc)
        assert expected_code == "NOT_FOUND"
    except oracledb.DatabaseError as exc:
        msg = str(exc)
        logger.info("Expected Oracle failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got: {msg}"
    except Exception as exc:
        msg = str(exc)
        logger.info("Expected generic failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got: {msg}"
    else:
        pytest.fail(f"Expected error {expected_code} did not occur")


def log_team_details(context: str, team) -> None:
    attrs = getattr(team, "attributes", None)
    details = {
        "context": context,
        "team_name": getattr(team, "team_name", None),
        "description": getattr(team, "description", None),
        "process": getattr(attrs, "process", None) if attrs else None,
        "agents": getattr(attrs, "agents", None) if attrs else None,
    }
    logger.info("TEAM_DETAILS: %s", details)
    print("TEAM_DETAILS:", details)


async def get_team_status(team_name: str):
    logger.info("Fetching team status for: %s", team_name)
    async with select_ai.async_cursor() as cur:
        await cur.execute(
            """
            SELECT status
            FROM USER_AI_AGENT_TEAMS
            WHERE agent_team_name = :team_name
            """,
            {"team_name": team_name},
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def assert_team_status(team_name: str, expected_status: str) -> None:
    status = await get_team_status(team_name)
    logger.info(
        "Verifying team status | team=%s | expected=%s | actual=%s",
        team_name,
        expected_status,
        status,
    )
    assert status == expected_status


# -----------------------------------------------------------------------------
# Test constants
# -----------------------------------------------------------------------------

PYSAI_TEAM_AGENT_NAME = f"PYSAI_TEAM_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_PROFILE_NAME = f"PYSAI_TEAM_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_TASK_NAME = f"PYSAI_TEAM_TASK_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_NAME = f"PYSAI_TEAM_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_DESC = "PYSAI ASYNC TEAM FINAL CONTRACT TEST"


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
async def python_gen_ai_profile(profile_attributes):
    logger.info("Creating profile: %s", PYSAI_TEAM_PROFILE_NAME)

    oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
    if oci_compartment_id:
        profile_attributes.oci_compartment_id = oci_compartment_id

    profile = await select_ai.AsyncProfile(
        profile_name=PYSAI_TEAM_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )

    yield profile

    logger.info("Deleting profile: %s", PYSAI_TEAM_PROFILE_NAME)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
def task_attributes():
    return TaskAttributes(
        instruction="Help the user. Question: {query}",
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
async def task(task_attributes):
    logger.info("Creating task: %s", PYSAI_TEAM_TASK_NAME)
    task_obj = AsyncTask(
        task_name=PYSAI_TEAM_TASK_NAME,
        description="Test Task",
        attributes=task_attributes,
    )
    await task_obj.create(replace=True)
    yield task_obj
    logger.info("Deleting task: %s", PYSAI_TEAM_TASK_NAME)
    await task_obj.delete(force=True)


@pytest.fixture(scope="module")
async def agent(python_gen_ai_profile):
    logger.info("Creating agent: %s", PYSAI_TEAM_AGENT_NAME)
    agent_obj = AsyncAgent(
        agent_name=PYSAI_TEAM_AGENT_NAME,
        description="Test Agent",
        attributes=AgentAttributes(
            profile_name=PYSAI_TEAM_PROFILE_NAME,
            role="You are a helpful AI assistant",
            enable_human_tool=False,
        ),
    )
    await agent_obj.create(enabled=True, replace=True)
    yield agent_obj
    logger.info("Deleting agent: %s", PYSAI_TEAM_AGENT_NAME)
    await agent_obj.delete(force=True)


@pytest.fixture(scope="module")
def team_attributes(agent, task):
    return TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )


@pytest.fixture(scope="module")
async def team(team_attributes):
    logger.info("Creating team: %s", PYSAI_TEAM_NAME)
    team_obj = AsyncTeam(
        team_name=PYSAI_TEAM_NAME,
        attributes=team_attributes,
        description=PYSAI_TEAM_DESC,
    )
    await team_obj.create(enabled=True, replace=True)
    yield team_obj
    logger.info("Deleting team: %s", PYSAI_TEAM_NAME)
    await team_obj.delete(force=True)


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

async def test_3300_create_and_identity(team, team_attributes):
    log_team_details("test_3300_create_and_identity", team)
    assert team.team_name == PYSAI_TEAM_NAME
    assert team.description == PYSAI_TEAM_DESC
    assert team.attributes == team_attributes


@pytest.mark.parametrize("pattern", [None, ".*", "^PYSAI_TEAM_"])
async def test_3301_list(pattern):
    logger.info("Listing teams using pattern: %s", pattern)
    teams = [t async for t in AsyncTeam.list(pattern)] if pattern else [t async for t in AsyncTeam.list()]
    for t in teams:
        if t.team_name == PYSAI_TEAM_NAME:
            log_team_details("test_3301_list", t)
    names = [t.team_name for t in teams]
    assert PYSAI_TEAM_NAME in names


async def test_3302_fetch(team_attributes):
    t = await AsyncTeam.fetch(PYSAI_TEAM_NAME)
    log_team_details("test_3302_fetch", t)
    assert t.attributes == team_attributes


async def test_3303_run(team):
    response = await team.run(
        prompt="What is 2+2?",
        params={"conversation_id": str(uuid.uuid4())},
    )
    logger.info("Team run response: %s", response)
    assert isinstance(response, str)
    assert len(response) > 0


async def test_3304_disable_enable_contract(team):
    logger.info("Disabling team: %s", team.team_name)
    await team.disable()
    await assert_team_status(team.team_name, "DISABLED")
    await expect_async_error("ORA-20053", lambda: team.disable())

    logger.info("Enabling team: %s", team.team_name)
    await team.enable()
    await assert_team_status(team.team_name, "ENABLED")
    await expect_async_error("ORA-20053", lambda: team.enable())


async def test_3305_set_attribute_process(team):
    await team.set_attribute("process", "sequential")
    fetched = await AsyncTeam.fetch(PYSAI_TEAM_NAME)
    log_team_details("test_3305_set_attribute_process", fetched)
    assert fetched.attributes.process == "sequential"


async def test_3306_set_attributes(team, agent, task):
    new_attrs = TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )
    await team.set_attributes(new_attrs)
    fetched = await AsyncTeam.fetch(PYSAI_TEAM_NAME)
    log_team_details("test_3306_set_attributes", fetched)
    assert fetched.attributes == new_attrs


async def test_3307_replace_create(team_attributes):
    team2 = AsyncTeam(PYSAI_TEAM_NAME, team_attributes, "REPLACED DESC")
    await team2.create(enabled=True, replace=True)
    fetched = await AsyncTeam.fetch(PYSAI_TEAM_NAME)
    log_team_details("test_3307_replace_create", fetched)
    assert fetched.description == "REPLACED DESC"


async def test_3308_fetch_non_existing():
    name = f"NO_SUCH_{uuid.uuid4().hex.upper()}"
    await expect_async_error("NOT_FOUND", lambda: AsyncTeam.fetch(name))


async def test_3311_set_attribute_invalid_key(team):
    await expect_async_error("ORA-20053", lambda: team.set_attribute("no_such_attr", "x"))


async def test_3312_set_attribute_none(team):
    await expect_async_error("ORA-20053", lambda: team.set_attribute("process", None))


async def test_3313_set_attribute_empty(team):
    await expect_async_error("ORA-20053", lambda: team.set_attribute("process", ""))


async def test_3314_set_attribute_invalid_value(team):
    await expect_async_error(
        "ORA-20053",
        lambda: team.set_attribute("process", "not_a_real_process"),
    )


async def test_3315_disable_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t = AsyncTeam(name, team_attributes, "TMP")
    await t.create()
    await t.delete(force=True)
    await expect_async_error("ORA-20053", lambda: t.disable())


async def test_3316_enable_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t = AsyncTeam(name, team_attributes, "TMP")
    await t.create()
    await t.delete(force=True)
    await expect_async_error("ORA-20053", lambda: t.enable())


async def test_3317_set_attribute_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t = AsyncTeam(name, team_attributes, "TMP")
    await t.create()
    await t.delete(force=True)
    await expect_async_error("ORA-20053", lambda: t.set_attribute("process", "sequential"))


async def test_3318_double_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t = AsyncTeam(name, team_attributes, "TMP")
    await t.create()
    await t.delete(force=True)
    await expect_async_error("ORA-20053", lambda: t.delete(force=False))


async def test_3319_create_existing_without_replace(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t1 = AsyncTeam(name, team_attributes, "TMP1")
    await t1.create(replace=False)
    await expect_async_error(
        "ORA-20053",
        lambda: AsyncTeam(name, team_attributes, "TMP2").create(replace=False),
    )
    await t1.delete(force=True)


async def test_3320_fetch_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex.upper()}"
    t = AsyncTeam(name, team_attributes, "TMP")
    await t.create()
    await t.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncTeam.fetch(name))
