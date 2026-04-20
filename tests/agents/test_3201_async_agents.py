# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3200 - Module for testing select_ai async agents
"""

import logging
import os
import uuid

import oracledb
import pytest
import select_ai
from select_ai.agent import AgentAttributes, AsyncAgent
from select_ai.errors import AgentNotFoundError

pytestmark = pytest.mark.anyio

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3201_async_agents.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

root = logging.getLogger()
root.setLevel(logging.INFO)
for handler in root.handlers[:]:
    root.removeHandler(handler)
file_handler = logging.FileHandler(LOG_FILE, mode="w")
file_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(file_handler)
logger = logging.getLogger()

PYSAI_3200_AGENT_NAME = f"PYSAI_3200_AGENT_{uuid.uuid4().hex.upper()}"
PYSAI_3200_AGENT_DESCRIPTION = "PYSAI_3200_AGENT_DESCRIPTION"
PYSAI_3200_PROFILE_NAME = f"PYSAI_3200_PROFILE_{uuid.uuid4().hex.upper()}"
PYSAI_3200_DISABLED_AGENT_NAME = (
    f"PYSAI_3200_DISABLED_AGENT_{uuid.uuid4().hex.upper()}"
)
PYSAI_3200_MISSING_AGENT_NAME = (
    f"PYSAI_3200_MISSING_AGENT_{uuid.uuid4().hex.upper()}"
)


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


def log_agent_details(context: str, agent) -> None:
    attrs = getattr(agent, "attributes", None)
    details = {
        "context": context,
        "agent_name": getattr(agent, "agent_name", None),
        "description": getattr(agent, "description", None),
        "profile_name": (
            getattr(attrs, "profile_name", None) if attrs else None
        ),
        "role": getattr(attrs, "role", None) if attrs else None,
        "enable_human_tool": (
            getattr(attrs, "enable_human_tool", None) if attrs else None
        ),
    }
    logger.info("AGENT_DETAILS: %s", details)
    print("AGENT_DETAILS:", details)


async def expect_async_error(expected_code, coro_fn):
    try:
        await coro_fn()
    except AgentNotFoundError as exc:
        logger.info("Expected failure (NOT_FOUND): %s", exc)
        assert expected_code == "NOT_FOUND"
    except oracledb.DatabaseError as exc:
        msg = str(exc)
        logger.info("Expected Oracle failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got: {msg}"
    else:
        pytest.fail(f"Expected error {expected_code} did not occur")


async def get_agent_status(agent_name):
    logger.info("Fetching agent status for: %s", agent_name)
    async with select_ai.async_cursor() as cur:
        await cur.execute(
            """
            SELECT status
            FROM USER_AI_AGENTS
            WHERE agent_name = :agent_name
            """,
            {"agent_name": agent_name},
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def assert_agent_status(agent_name: str, expected_status: str) -> None:
    status = await get_agent_status(agent_name)
    logger.info(
        "Verifying agent status | agent=%s | expected=%s | actual=%s",
        agent_name,
        expected_status,
        status,
    )
    assert status == expected_status


@pytest.fixture(scope="module")
async def async_python_gen_ai_profile(profile_attributes):
    logger.info("Creating profile: %s", PYSAI_3200_PROFILE_NAME)
    profile = await select_ai.AsyncProfile(
        profile_name=PYSAI_3200_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    logger.info("Deleting profile: %s", PYSAI_3200_PROFILE_NAME)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
def agent_attributes():
    return AgentAttributes(
        profile_name=PYSAI_3200_PROFILE_NAME,
        role=(
            "You are an AI Movie Analyst. "
            "You can help answer movie-related questions."
        ),
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
async def agent(async_python_gen_ai_profile, agent_attributes):
    logger.info("Creating async agent: %s", PYSAI_3200_AGENT_NAME)
    agent_obj = AsyncAgent(
        agent_name=PYSAI_3200_AGENT_NAME,
        attributes=agent_attributes,
        description=PYSAI_3200_AGENT_DESCRIPTION,
    )
    await agent_obj.create(enabled=True, replace=True)
    yield agent_obj
    logger.info("Deleting async agent: %s", PYSAI_3200_AGENT_NAME)
    await agent_obj.delete(force=True)


async def test_3200_identity(agent, agent_attributes):
    log_agent_details("test_3200_identity", agent)
    assert agent.agent_name == PYSAI_3200_AGENT_NAME
    assert agent.attributes == agent_attributes
    assert agent.description == PYSAI_3200_AGENT_DESCRIPTION
    assert agent.attributes.enable_human_tool is False


@pytest.mark.parametrize(
    "agent_name_pattern", [None, ".*", "^PYSAI_3200_AGENT_"]
)
async def test_3201_list(agent_name_pattern):
    logger.info("Listing agents with pattern=%s", agent_name_pattern)
    if agent_name_pattern:
        agents = [
            a
            async for a in select_ai.agent.AsyncAgent.list(agent_name_pattern)
        ]
    else:
        agents = [a async for a in select_ai.agent.AsyncAgent.list()]

    for a in agents:
        if a.agent_name == PYSAI_3200_AGENT_NAME:
            log_agent_details("test_3201_list", a)

    agent_names = set(a.agent_name for a in agents)
    agent_descriptions = set(a.description for a in agents)
    assert len(agents) >= 1
    assert PYSAI_3200_AGENT_NAME in agent_names
    assert PYSAI_3200_AGENT_DESCRIPTION in agent_descriptions


async def test_3202_fetch(agent_attributes):
    a = await AsyncAgent.fetch(agent_name=PYSAI_3200_AGENT_NAME)
    log_agent_details("test_3202_fetch", a)
    assert a.agent_name == PYSAI_3200_AGENT_NAME
    assert a.attributes == agent_attributes
    assert a.description == PYSAI_3200_AGENT_DESCRIPTION


async def test_3203_fetch_non_existing():
    name = f"PYSAI_NO_SUCH_AGENT_{uuid.uuid4().hex.upper()}"
    logger.info("Fetching non-existing async agent: %s", name)
    with pytest.raises(AgentNotFoundError) as exc:
        await AsyncAgent.fetch(name)
    logger.info("Received expected error: %s", exc.value)


async def test_3204_create_agent_default_status_enabled(agent_attributes):
    name = f"PYSAI_3200_STATUS_ENABLED_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(
        agent_name=name,
        description="Default enabled status",
        attributes=agent_attributes,
    )
    await a.create(replace=True)
    try:
        await assert_agent_status(name, "ENABLED")
        fetched = await AsyncAgent.fetch(name)
        log_agent_details(
            "test_3204_create_agent_default_status_enabled", fetched
        )
        assert fetched.description == "Default enabled status"
    finally:
        await a.delete(force=True)


async def test_3205_create_agent_with_enabled_false_sets_disabled(
    agent_attributes,
):
    a = AsyncAgent(
        agent_name=PYSAI_3200_DISABLED_AGENT_NAME,
        description="Initially disabled",
        attributes=agent_attributes,
    )
    await a.create(enabled=False, replace=True)
    try:
        await assert_agent_status(PYSAI_3200_DISABLED_AGENT_NAME, "DISABLED")
        fetched = await AsyncAgent.fetch(PYSAI_3200_DISABLED_AGENT_NAME)
        log_agent_details(
            "test_3205_create_agent_with_enabled_false_sets_disabled", fetched
        )
        assert fetched.description == "Initially disabled"
    finally:
        await a.delete(force=True)


async def test_3206_set_attribute(agent):
    logger.info("Setting role attribute on async agent: %s", agent.agent_name)
    await agent.set_attribute("role", "You are a DB assistant")
    updated = await AsyncAgent.fetch(PYSAI_3200_AGENT_NAME)
    log_agent_details("test_3206_set_attribute", updated)
    assert "DB assistant" in updated.attributes.role


async def test_3207_set_attributes(agent):
    logger.info("Replacing async agent attributes")
    new_attrs = AgentAttributes(
        profile_name=PYSAI_3200_PROFILE_NAME,
        role="You are a cloud architect",
        enable_human_tool=True,
    )
    await agent.set_attributes(new_attrs)
    updated = await AsyncAgent.fetch(PYSAI_3200_AGENT_NAME)
    log_agent_details("test_3207_set_attributes", updated)
    assert updated.attributes == new_attrs


async def test_3208_set_attribute_invalid_key(agent):
    logger.info("Setting invalid attribute key on async agent")
    with pytest.raises(oracledb.DatabaseError) as exc:
        await agent.set_attribute("no_such_key", 123)
    logger.info("Received expected Oracle error: %s", exc.value)
    assert "ORA-20050" in str(exc.value)


async def test_3209_drop_agent_force_true_non_existent():
    logger.info("Dropping missing agent with force=True")
    a = AsyncAgent(agent_name=PYSAI_3200_MISSING_AGENT_NAME)
    await a.delete(force=True)
    status = await get_agent_status(PYSAI_3200_MISSING_AGENT_NAME)
    logger.info("Status after force delete on missing agent: %s", status)
    assert status is None


async def test_3210_drop_agent_force_false_non_existent_raises():
    logger.info("Dropping missing agent with force=False")
    a = AsyncAgent(agent_name=PYSAI_3200_MISSING_AGENT_NAME)
    with pytest.raises(oracledb.DatabaseError) as exc:
        await a.delete(force=False)
    logger.info("Received expected Oracle error: %s", exc.value)


async def test_3211_create_requires_agent_name(agent_attributes):
    logger.info("Validating async create() requires agent_name")
    with pytest.raises(AttributeError) as exc:
        await AsyncAgent(attributes=agent_attributes).create()
    logger.info("Received expected error: %s", exc.value)


async def test_3212_create_requires_attributes():
    logger.info("Validating async create() requires attributes")
    with pytest.raises(AttributeError) as exc:
        await AsyncAgent(
            agent_name=f"PYSAI_3200_NO_ATTR_{uuid.uuid4().hex.upper()}"
        ).create()
    logger.info("Received expected error: %s", exc.value)


async def test_3213_disable_enable(agent):
    logger.info("Disabling async agent: %s", agent.agent_name)
    await agent.disable()
    await assert_agent_status(agent.agent_name, "DISABLED")

    logger.info("Enabling async agent: %s", agent.agent_name)
    await agent.enable()
    await assert_agent_status(agent.agent_name, "ENABLED")


async def test_3214_set_attribute_none(agent):
    logger.info("Setting role=None on async agent: %s", agent.agent_name)
    await expect_async_error(
        "ORA-20050", lambda: agent.set_attribute("role", None)
    )


async def test_3215_set_attribute_empty(agent):
    logger.info("Setting role='' on async agent: %s", agent.agent_name)
    await expect_async_error(
        "ORA-20050", lambda: agent.set_attribute("role", "")
    )


async def test_3216_create_existing_without_replace(agent_attributes):
    logger.info("Creating duplicate async agent without replace")
    dup = AsyncAgent(
        agent_name=PYSAI_3200_AGENT_NAME,
        description="Duplicate async agent",
        attributes=agent_attributes,
    )
    await expect_async_error("ORA-20050", lambda: dup.create(replace=False))


async def test_3217_delete_and_recreate(agent_attributes):
    name = f"PYSAI_RECREATE_{uuid.uuid4().hex.upper()}"
    logger.info("Creating async agent: %s", name)
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()

    fetched = await AsyncAgent.fetch(name)
    log_agent_details("test_3217_created", fetched)
    assert fetched.agent_name == name

    logger.info("Deleting async agent: %s", name)
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))

    logger.info("Recreating async agent: %s", name)
    await a.create(replace=False)
    recreated = await AsyncAgent.fetch(name)
    log_agent_details("test_3217_recreated", recreated)
    assert recreated.agent_name == name

    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))


async def test_3218_disable_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))
    await expect_async_error("ORA-20050", lambda: a.disable())


async def test_3219_enable_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))
    await expect_async_error("ORA-20050", lambda: a.enable())


async def test_3220_set_attribute_after_delete(agent_attributes):
    name = f"PYSAI_TMP_DEL_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))
    await expect_async_error("ORA-20050", lambda: a.set_attribute("role", "X"))


async def test_3221_double_delete_force_true(agent_attributes):
    name = f"PYSAI_TMP_DOUBLE_DEL_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))


async def test_3222_double_delete_force_false_raises(agent_attributes):
    name = f"PYSAI_TMP_DOUBLE_DEL_FALSE_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=False)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))
    await expect_async_error("ORA-20050", lambda: a.delete(force=False))


async def test_3223_fetch_after_delete(agent_attributes):
    name = f"PYSAI_TMP_FETCH_DEL_{uuid.uuid4().hex.upper()}"
    a = AsyncAgent(name, attributes=agent_attributes)
    await a.create()
    await a.delete(force=True)
    await expect_async_error("NOT_FOUND", lambda: AsyncAgent.fetch(name))


async def test_3224_list_all_non_empty():
    logger.info("Listing all async agents")
    agents = [a async for a in AsyncAgent.list()]
    names = sorted(a.agent_name for a in agents)
    logger.info("Total async agents found: %d", len(names))
    for name in names:
        logger.info("  - %s", name)
    assert len(names) > 0
