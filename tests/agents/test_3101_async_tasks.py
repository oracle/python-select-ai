# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3101 - Module for testing select_ai agent async tasks
"""

import uuid
import logging
import os

import oracledb
import pytest
import select_ai
from select_ai.agent import AsyncTask, TaskAttributes

pytestmark = pytest.mark.anyio

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3101_async_tasks.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

root = logging.getLogger()
root.setLevel(logging.INFO)
for handler in root.handlers[:]:
    root.removeHandler(handler)
file_handler = logging.FileHandler(LOG_FILE, mode="w")
file_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(file_handler)
logger = logging.getLogger()

PYSAI_3100_TASK_NAME = f"PYSAI_3100_{uuid.uuid4().hex.upper()}"
PYSAI_3100_SQL_TASK_DESCRIPTION = "PYSAI_3100_SQL_TASK_DESCRIPTION"
PYSAI_3100_DISABLED_TASK_NAME = f"PYSAI_3100_DISABLED_{uuid.uuid4().hex.upper()}"
PYSAI_3100_DEFAULT_STATUS_TASK_NAME = (
    f"PYSAI_3100_DEFAULT_STATUS_{uuid.uuid4().hex.upper()}"
)
PYSAI_3100_PARENT_TASK_NAME = f"PYSAI_3100_PARENT_{uuid.uuid4().hex.upper()}"
PYSAI_3100_CHILD_TASK_NAME = f"PYSAI_3100_CHILD_{uuid.uuid4().hex.upper()}"
PYSAI_3100_DEFAULT_HUMAN_TASK_NAME = (
    f"PYSAI_3100_DEFAULT_HUMAN_{uuid.uuid4().hex.upper()}"
)
PYSAI_3100_MISSING_TASK_NAME = f"PYSAI_3100_MISSING_{uuid.uuid4().hex.upper()}"


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


async def get_task_status(task_name):
    logger.info("Fetching task status for: %s", task_name)
    async with select_ai.async_cursor() as cur:
        await cur.execute(
            """
            SELECT status
            FROM USER_AI_AGENT_TASKS
            WHERE task_name = :task_name
            """,
            {"task_name": task_name},
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def assert_task_status(task_name: str, expected_status: str) -> None:
    status = await get_task_status(task_name)
    logger.info(
        "Verifying task status | task=%s | expected=%s | actual=%s",
        task_name,
        expected_status,
        status,
    )
    assert status == expected_status


def log_task_details(context: str, task) -> None:
    attrs = getattr(task, "attributes", None)
    details = {
        "context": context,
        "task_name": getattr(task, "task_name", None),
        "description": getattr(task, "description", None),
        "instruction": getattr(attrs, "instruction", None) if attrs else None,
        "tools": getattr(attrs, "tools", None) if attrs else None,
        "input": getattr(attrs, "input", None) if attrs else None,
        "enable_human_tool": (
            getattr(attrs, "enable_human_tool", None) if attrs else None
        ),
    }
    logger.info("TASK_DETAILS: %s", details)
    print("TASK_DETAILS:", details)


@pytest.fixture(scope="module")
def task_attributes():
    return TaskAttributes(
        instruction="Help the user with their request about movies. "
        "User question: {query}. "
        "You can use SQL tool to search the data from database",
        tools=["MOVIE_SQL_TOOL"],
        enable_human_tool=False,
    )


@pytest.fixture(scope="module")
async def task(task_attributes):
    task = AsyncTask(
        task_name=PYSAI_3100_TASK_NAME,
        description=PYSAI_3100_SQL_TASK_DESCRIPTION,
        attributes=task_attributes,
    )
    await task.create()
    yield task
    await task.delete(force=True)


async def test_3100(task, task_attributes):
    """simple task creation"""
    log_task_details("test_3100", task)
    assert task.task_name == PYSAI_3100_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3100_SQL_TASK_DESCRIPTION
    assert task.attributes.instruction is not None
    assert "{query}" in task.attributes.instruction
    assert task.attributes.tools == ["MOVIE_SQL_TOOL"]
    assert task.attributes.enable_human_tool is False


@pytest.mark.parametrize("task_name_pattern", [None, "^PYSAI_3100_"])
async def test_3101(task_name_pattern):
    """task list"""
    if task_name_pattern:
        tasks = [task async for task in select_ai.agent.AsyncTask.list(task_name_pattern)]
    else:
        tasks = [task async for task in select_ai.agent.AsyncTask.list()]
    for task in tasks:
        if task.task_name == PYSAI_3100_TASK_NAME:
            log_task_details("test_3101", task)
    task_names = set(task.task_name for task in tasks)
    task_descriptions = set(task.description for task in tasks)
    assert len(tasks) >= 1
    assert PYSAI_3100_TASK_NAME in task_names
    assert PYSAI_3100_SQL_TASK_DESCRIPTION in task_descriptions


async def test_3102(task_attributes):
    """task fetch"""
    task = await select_ai.agent.AsyncTask.fetch(PYSAI_3100_TASK_NAME)
    log_task_details("test_3102", task)
    assert task.task_name == PYSAI_3100_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3100_SQL_TASK_DESCRIPTION
    assert task.attributes.tools == ["MOVIE_SQL_TOOL"]
    assert task.attributes.input is None
    assert task.attributes.enable_human_tool is False


async def test_3103_create_task_default_status_enabled():
    task = AsyncTask(
        task_name=PYSAI_3100_DEFAULT_STATUS_TASK_NAME,
        description="Default status should be enabled",
        attributes=TaskAttributes(
            instruction="Summarize user request: {query}",
            tools=["MOVIE_SQL_TOOL"],
            enable_human_tool=False,
        ),
    )
    await task.create(replace=True)
    try:
        await assert_task_status(PYSAI_3100_DEFAULT_STATUS_TASK_NAME, "ENABLED")
        fetched = await AsyncTask.fetch(PYSAI_3100_DEFAULT_STATUS_TASK_NAME)
        log_task_details("test_3103", fetched)
        assert fetched.description == "Default status should be enabled"
        assert fetched.attributes.enable_human_tool is False
    finally:
        await task.delete(force=True)


async def test_3104_create_task_with_enabled_false_sets_disabled():
    task = AsyncTask(
        task_name=PYSAI_3100_DISABLED_TASK_NAME,
        description="Task created disabled",
        attributes=TaskAttributes(
            instruction="Handle disabled task validation",
            tools=["MOVIE_SQL_TOOL"],
            enable_human_tool=False,
        ),
    )
    await task.create(enabled=False, replace=True)
    try:
        await assert_task_status(PYSAI_3100_DISABLED_TASK_NAME, "DISABLED")
        fetched = await AsyncTask.fetch(PYSAI_3100_DISABLED_TASK_NAME)
        log_task_details("test_3104", fetched)
        assert fetched.description == "Task created disabled"

        logger.info("Enabling task created with enabled=False: %s", task.task_name)
        await task.enable()
        await assert_task_status(PYSAI_3100_DISABLED_TASK_NAME, "ENABLED")
    finally:
        await task.delete(force=True)


async def test_3105_disable_enable_task(task):
    logger.info("Disabling task: %s", task.task_name)
    await task.disable()
    await assert_task_status(PYSAI_3100_TASK_NAME, "DISABLED")

    logger.info("Enabling task: %s", task.task_name)
    await task.enable()
    await assert_task_status(PYSAI_3100_TASK_NAME, "ENABLED")


async def test_3105b_set_single_attribute_invalid(task):
    logger.info("Setting invalid single attribute for async task: %s", task.task_name)
    with pytest.raises(oracledb.DatabaseError) as exc:
        await task.set_attribute("description", "New Desc")
    logger.info("Received expected Oracle error: %s", exc.value)
    assert "ORA-20051" in str(exc.value)


async def test_3105c_duplicate_task_creation_fails(task):
    logger.info("Creating duplicate async task without replace: %s", task.task_name)
    dup = AsyncTask(
        task_name=task.task_name,
        description="Duplicate task",
        attributes=task.attributes,
    )
    with pytest.raises(oracledb.Error) as exc:
        await dup.create(replace=False)
    logger.info("Received expected duplicate create error: %s", exc.value)
    assert "ORA-20051" in str(exc.value)


async def test_3105d_invalid_regex_pattern():
    logger.info("Listing async tasks with invalid regex")
    with pytest.raises(oracledb.Error) as exc:
        async for _ in AsyncTask.list("[INVALID_REGEX"):
            pass
    logger.info("Received expected invalid regex error: %s", exc.value)
    assert "ORA-12726" in str(exc.value)


async def test_3106_drop_task_force_true_non_existent():
    logger.info("Dropping missing task with force=True: %s", PYSAI_3100_MISSING_TASK_NAME)
    task = AsyncTask(task_name=PYSAI_3100_MISSING_TASK_NAME)
    await task.delete(force=True)
    status = await get_task_status(PYSAI_3100_MISSING_TASK_NAME)
    logger.info("Status after force delete on missing task: %s", status)
    assert status is None


async def test_3107_drop_task_force_false_non_existent_raises():
    logger.info("Dropping missing task with force=False: %s", PYSAI_3100_MISSING_TASK_NAME)
    task = AsyncTask(task_name=PYSAI_3100_MISSING_TASK_NAME)
    with pytest.raises(oracledb.Error) as exc:
        await task.delete(force=False)
    logger.info("Received expected drop error: %s", exc.value)


async def test_3108_create_task_with_input_attribute():
    logger.info("Creating parent/child tasks for input chaining validation")
    parent_task = AsyncTask(
        task_name=PYSAI_3100_PARENT_TASK_NAME,
        description="Parent task",
        attributes=TaskAttributes(
            instruction="Generate an intermediate summary for: {query}",
            tools=["MOVIE_SQL_TOOL"],
            enable_human_tool=False,
        ),
    )
    child_task = AsyncTask(
        task_name=PYSAI_3100_CHILD_TASK_NAME,
        description="Child task with input dependency",
        attributes=TaskAttributes(
            instruction="Use upstream context and produce final answer",
            tools=["MOVIE_SQL_TOOL"],
            input=PYSAI_3100_PARENT_TASK_NAME,
            enable_human_tool=False,
        ),
    )
    await parent_task.create(replace=True)
    await child_task.create(replace=True)
    try:
        fetched = await AsyncTask.fetch(PYSAI_3100_CHILD_TASK_NAME)
        log_task_details("test_3108_child", fetched)
        assert fetched.attributes.input == PYSAI_3100_PARENT_TASK_NAME
        assert fetched.attributes.tools == ["MOVIE_SQL_TOOL"]
        assert fetched.description == "Child task with input dependency"
        assert fetched.attributes.enable_human_tool is False
    finally:
        await child_task.delete(force=True)
        await parent_task.delete(force=True)


async def test_3109_enable_human_tool_default_true():
    logger.info("Creating task to validate enable_human_tool default behavior")
    task = AsyncTask(
        task_name=PYSAI_3100_DEFAULT_HUMAN_TASK_NAME,
        description="Default enable_human_tool check",
        attributes=TaskAttributes(
            instruction="Collect more details from user for: {query}",
            tools=["MOVIE_SQL_TOOL"],
        ),
    )
    await task.create(replace=True)
    try:
        fetched = await AsyncTask.fetch(PYSAI_3100_DEFAULT_HUMAN_TASK_NAME)
        log_task_details("test_3109", fetched)
        assert fetched.attributes.enable_human_tool is True
    finally:
        await task.delete(force=True)


async def test_3110_create_requires_task_name():
    logger.info("Validating create() requires task_name")
    with pytest.raises(AttributeError) as exc:
        await AsyncTask(
            attributes=TaskAttributes(
                instruction="Missing task_name validation", tools=[]
            )
        ).create()
    logger.info("Received expected error: %s", exc.value)


async def test_3111_create_requires_attributes():
    logger.info("Validating create() requires attributes")
    with pytest.raises(AttributeError) as exc:
        await AsyncTask(
            task_name=f"PYSAI_3100_NO_ATTR_{uuid.uuid4().hex.upper()}"
        ).create()
    logger.info("Received expected error: %s", exc.value)


async def test_3112_enable_deleted_task_object_raises():
    logger.info("Creating task to validate object behavior after delete")
    task_name = f"PYSAI_3100_DELETED_{uuid.uuid4().hex.upper()}"
    attrs = TaskAttributes(
        instruction="Validate task object after delete for: {query}",
        tools=["MOVIE_SQL_TOOL"],
        enable_human_tool=False,
    )
    task = AsyncTask(
        task_name=task_name,
        description="Task deleted before reuse",
        attributes=attrs,
    )

    await task.create(replace=True)
    await assert_task_status(task_name, "ENABLED")

    await task.delete(force=True)
    status = await get_task_status(task_name)
    logger.info("Task status after delete: %s", status)
    assert status is None

    logger.info("Verifying in-memory task object is still populated")
    assert task.task_name == task_name
    assert task.description == "Task deleted before reuse"
    assert task.attributes == attrs

    logger.info("Attempting to enable deleted task using same object")
    with pytest.raises(oracledb.DatabaseError) as exc:
        await task.enable()
    logger.info("Received expected error when enabling deleted task: %s", exc.value)
    assert "ORA-20051" in str(exc.value)
