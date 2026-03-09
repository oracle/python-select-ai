# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0
# -----------------------------------------------------------------------------

"""
3301 - Final contract, regression and corner-case tests for select_ai.agent.Team
"""

import uuid
import logging
import os
import pytest
import select_ai
import oracledb

from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
)

from select_ai.errors import AgentTeamNotFoundError

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_DIR = os.path.join(PROJECT_ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "tkex_test_3301_teams.log")

root = logging.getLogger()
root.setLevel(logging.INFO)

for h in root.handlers[:]:
    root.removeHandler(h)

fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

def log_step(msg):
    LOGGER.info("%s", msg)

def log_ok(msg):
    LOGGER.info("%s", msg)
logger = LOGGER


# -----------------------------------------------------------------------------
# Per-test logging
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


# -----------------------------------------------------------------------------
# Strict error checker (LIKE 3101 / 3201)
# -----------------------------------------------------------------------------

def expect_error(expected_code, fn):
    """
    expected_code:
      - "NOT_FOUND"
      - "ORA-20051"
      - "ORA-xxxxx"
    """
    try:
        fn()
    except AgentTeamNotFoundError as e:
        LOGGER.info("Expected failure (NOT_FOUND): %s", e)
        assert expected_code == "NOT_FOUND"
    except oracledb.DatabaseError as e:
        msg = str(e)
        LOGGER.info("Expected Oracle failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got: {msg}"
    except Exception as e:
        LOGGER.info("Expected generic failure: %s", e)
        assert expected_code in str(e), f"Expected {expected_code}, got: {e}"
    else:
        pytest.fail(f"Expected error {expected_code} did not occur")

# -----------------------------------------------------------------------------
# Test constants
# -----------------------------------------------------------------------------

PYSAI_TEAM_AGENT_NAME = f"PYSAI_TEAM_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_PROFILE_NAME = f"PYSAI_TEAM_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_TASK_NAME = f"PYSAI_TEAM_TASK_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_NAME = f"PYSAI_TEAM_{uuid.uuid4().hex.upper()}"
PYSAI_TEAM_DESC = "PYSAI TEAM FINAL CONTRACT TEST"

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

# @pytest.fixture(scope="module", autouse=True)
# def _connect():
#     select_ai.connect()
#     yield
#     select_ai.disconnect()

# @pytest.fixture(scope="module")
# def profile_attributes():
#     return {
#         "provider": "oci_genai",
#         "model": "cohere.command-r-plus"
#     }

@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    log_step(f"Creating profile: {PYSAI_TEAM_PROFILE_NAME}")

    oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
    if not oci_compartment_id:
        raise RuntimeError("PYSAI_TEST_OCI_COMPARTMENT_ID not set")

    # ---- EXTEND existing ProfileAttributes object ----
    profile_attributes.oci_compartment_id = oci_compartment_id

    # ---- STRICT TYPE CHECK ----
    assert isinstance(
        profile_attributes,
        select_ai.ProfileAttributes
    ), "profile_attributes must be ProfileAttributes object"

    profile = select_ai.Profile(
        profile_name=PYSAI_TEAM_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,  # <-- pass object, NOT dict
    )

    profile.create(replace=True)

    yield profile

    log_step(f"Deleting profile: {PYSAI_TEAM_PROFILE_NAME}")
    profile.delete(force=True)


@pytest.fixture(scope="module")
def task_attributes():
    return TaskAttributes(
        instruction="Help the user. Question: {query}",
        enable_human_tool=False,
    )

@pytest.fixture(scope="module")
def task(task_attributes):
    log_step(f"Creating task: {PYSAI_TEAM_TASK_NAME}")
    task = Task(
        task_name=PYSAI_TEAM_TASK_NAME,
        description="Test Task",
        attributes=task_attributes,
    )
    task.create(replace=True)
    yield task
    log_step(f"Deleting task: {PYSAI_TEAM_TASK_NAME}")
    task.delete(force=True)

@pytest.fixture(scope="module")
def agent(python_gen_ai_profile):
    log_step(f"Creating agent: {PYSAI_TEAM_AGENT_NAME}")
    agent = Agent(
        agent_name=PYSAI_TEAM_AGENT_NAME,
        description="Test Agent",
        attributes=AgentAttributes(
            profile_name=PYSAI_TEAM_PROFILE_NAME,
            role="You are a helpful AI assistant",
            enable_human_tool=False,
        ),
    )
    agent.create(enabled=True, replace=True)
    yield agent
    log_step(f"Deleting agent: {PYSAI_TEAM_AGENT_NAME}")
    agent.delete(force=True)

@pytest.fixture(scope="module")
def team_attributes(agent, task):
    return TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )

@pytest.fixture(scope="module")
def team(team_attributes):
    log_step(f"Creating team: {PYSAI_TEAM_NAME}")
    team = Team(
        team_name=PYSAI_TEAM_NAME,
        attributes=team_attributes,
        description=PYSAI_TEAM_DESC,
    )
    team.create(enabled=True, replace=True)
    yield team
    log_step(f"Deleting team: {PYSAI_TEAM_NAME}")
    team.delete(force=True)

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Logging-enhanced Team tests
# -----------------------------------------------------------------------------

def test_3300_create_and_identity(team, team_attributes):
    log_step("Validating team identity and attributes")
    log_step(f"Team name: {team.team_name}")
    log_step(f"Team description: {team.description}")
    log_step(f"Team attributes: {team.attributes}")
    assert team.team_name == PYSAI_TEAM_NAME
    assert team.description == PYSAI_TEAM_DESC
    assert team.attributes == team_attributes
    log_ok("Team identity and attributes OK")


@pytest.mark.parametrize("pattern", [None, ".*", "^PYSAI_TEAM_"])
def test_3301_list(pattern):
    log_step(f"Listing teams using pattern: {pattern}")
    teams = list(Team.list(pattern)) if pattern else list(Team.list())
    names = [t.team_name for t in teams]
    log_step(f"Teams found: {names}")
    assert PYSAI_TEAM_NAME in names
    log_ok("Team found in list")


def test_3302_fetch(team_attributes):
    log_step(f"Fetching team: {PYSAI_TEAM_NAME}")
    t = Team.fetch(PYSAI_TEAM_NAME)
    log_step(f"Fetched team attributes: {t.attributes}")
    assert t.attributes == team_attributes
    log_ok("Fetch OK")


def test_3303_run(team):
    log_step(f"Running team: {team.team_name}")
    response = team.run("What is 2+2?", {"conversation_id": str(uuid.uuid4())})
    log_step(f"Team run response: {response}")
    assert isinstance(response, str)
    assert len(response) > 0
    log_ok("Run OK")


def test_3304_disable_enable_contract(team):
    log_step(f"Disabling team: {team.team_name}")
    team.disable()
    log_step("Team disabled successfully")
    expect_error("ORA-20053", lambda: team.disable())
    log_step(f"Enabling team: {team.team_name}")
    team.enable()
    log_step("Team enabled successfully")
    expect_error("ORA-20053", lambda: team.enable())


def test_3305_set_attribute_process(team):
    log_step(f"Setting team attribute 'process' to 'sequential': {team.team_name}")
    team.set_attribute("process", "sequential")
    fetched = Team.fetch(PYSAI_TEAM_NAME)
    log_step(f"Fetched attribute process: {fetched.attributes.process}")
    assert fetched.attributes.process == "sequential"
    log_ok("Set attribute OK")


def test_3306_set_attributes(team, agent, task):
    new_attrs = TeamAttributes(
        agents=[{"name": agent.agent_name, "task": task.task_name}],
        process="sequential",
    )
    log_step(f"Replacing team attributes: {team.team_name}")
    log_step(f"New attributes: {new_attrs}")
    team.set_attributes(new_attrs)
    fetched = Team.fetch(PYSAI_TEAM_NAME)
    log_step(f"Fetched attributes after replace: {fetched.attributes}")
    assert fetched.attributes == new_attrs
    log_ok("Set attributes OK")


def test_3307_replace_create(team_attributes):
    log_step(f"Replacing existing team: {PYSAI_TEAM_NAME}")
    team2 = Team(PYSAI_TEAM_NAME, team_attributes, "REPLACED DESC")
    team2.create(enabled=True, replace=True)
    fetched = Team.fetch(PYSAI_TEAM_NAME)
    log_step(f"Fetched team description after replace: {fetched.description}")
    assert fetched.description == "REPLACED DESC"
    log_ok("Replace OK")


def test_3308_fetch_non_existing():
    name = f"NO_SUCH_{uuid.uuid4().hex}"
    log_step(f"Fetching non-existing team: {name}")
    expect_error("NOT_FOUND", lambda: Team.fetch(name))
    log_ok("Fetch non-existing confirmed error")


def test_3311_set_attribute_invalid_key(team):
    log_step(f"Setting invalid attribute key on team: {team.team_name}")
    expect_error("ORA-20053", lambda: team.set_attribute("no_such_attr", "x"))
    log_ok("Set invalid attribute confirmed error")


def test_3312_set_attribute_none(team):
    log_step(f"Setting team attribute 'process' to None: {team.team_name}")
    expect_error("ORA-20053", lambda: team.set_attribute("process", None))
    log_ok("Set attribute None confirmed error")


def test_3313_set_attribute_empty(team):
    log_step(f"Setting team attribute 'process' to empty string: {team.team_name}")
    expect_error("ORA-20053", lambda: team.set_attribute("process", ""))
    log_ok("Set attribute empty confirmed error")


def test_3314_set_attribute_invalid_value(team):
    log_step(f"Setting team attribute 'process' to invalid value: {team.team_name}")
    expect_error("ORA-20053", lambda: team.set_attribute("process", "not_a_real_process"))
    log_ok("Set attribute invalid value confirmed error")


def test_3315_disable_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting temporary team: {name}")
    t.delete(force=True)
    log_step(f"Attempting to disable deleted team: {name}")
    expect_error("ORA-20053", lambda: t.disable())
    log_ok("Disable after delete confirmed error")


def test_3316_enable_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting temporary team: {name}")
    t.delete(force=True)
    log_step(f"Attempting to enable deleted team: {name}")
    expect_error("ORA-20053", lambda: t.enable())
    log_ok("Enable after delete confirmed error")


def test_3317_set_attribute_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting temporary team: {name}")
    t.delete(force=True)
    log_step(f"Attempting to set attribute on deleted team: {name}")
    expect_error("ORA-20053", lambda: t.set_attribute("process", "sequential"))
    log_ok("Set attribute after delete confirmed error")


def test_3318_double_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting team first time: {name}")
    t.delete(force=True)
    log_step(f"Deleting team second time: {name}")
    expect_error("ORA-20053", lambda: t.delete(force=False))
    log_ok("Double delete confirmed error")


def test_3319_create_existing_without_replace(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating team: {name}")
    t1 = Team(name, team_attributes, "TMP1")
    t1.create(replace=False)
    log_step(f"Attempting to create existing team without replace: {name}")
    expect_error("ORA-20053", lambda: Team(name, team_attributes, "TMP2").create(replace=False))
    t1.delete(force=True)
    log_ok("Create existing without replace confirmed error")


def test_3320_fetch_after_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting temporary team: {name}")
    t.delete(force=True)
    log_step(f"Fetching deleted team: {name}")
    expect_error("NOT_FOUND", lambda: Team.fetch(name))
    log_ok("Fetch after delete confirmed error")


def test_3321_double_delete(team_attributes):
    name = f"TMP_{uuid.uuid4().hex}"
    log_step(f"Creating temporary team: {name}")
    t = Team(name, team_attributes, "TMP")
    t.create()
    log_step(f"Deleting team first time: {name}")
    t.delete(force=True)
    log_step(f"Deleting team second time: {name}")
    # Second delete without force to actually raise the error
    expect_error("ORA-20053", lambda: t.delete(force=False))
    log_ok("Double delete confirmed error")
