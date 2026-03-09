# -----------------------------------------------------------------------------
# 3101 - Comprehensive tests for select_ai.agent.Task with error code asserts
# -----------------------------------------------------------------------------

import uuid
import logging
import pytest
import os
import select_ai
from select_ai.agent import Task, TaskAttributes
from select_ai.errors import AgentTaskNotFoundError
import oracledb
# Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3101_tasks.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Logging
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

def get_task_status(task_name):
    with select_ai.cursor() as cur:
        cur.execute("""
            SELECT status
            FROM USER_AI_AGENT_TASKS
            WHERE task_name = :task_name
        """, {"task_name": task_name})
        row = cur.fetchone()
        return row[0] if row else None

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

BASE = f"PYSAI_3101_{uuid.uuid4().hex.upper()}"
TASK_A_NAME = f"{BASE}_TASK_A"
TASK_B_NAME = f"{BASE}_TASK_B"

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
    except AgentTaskNotFoundError as e:
        logger.info("Expected failure (NOT_FOUND): %s", e)
        assert expected_code == "NOT_FOUND"
    except oracledb.DatabaseError as e:
        msg = str(e)
        logger.info("Expected Oracle failure: %s", msg)
        assert expected_code in msg, f"Expected {expected_code}, got {msg}"
    else:
        pytest.fail(f"Expected error {expected_code} did not occur")


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def task_a():
    logger.info("Creating TASK_A: %s", TASK_A_NAME)
    attrs = TaskAttributes(
        instruction="Analyze movie data for user query: {query}",
        tools=["MOVIE_SQL_TOOL"],
        enable_human_tool=False,
    )
    task = Task(task_name=TASK_A_NAME, description="Primary analysis task", attributes=attrs)
    task.create()
    logger.info("TASK_A created successfully")
    yield task
    logger.info("Deleting TASK_A: %s", TASK_A_NAME)
    task.delete(force=True)
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(TASK_A_NAME))
    logger.info("TASK_A deleted successfully")

@pytest.fixture(scope="module")
def task_b(task_a):
    logger.info("Creating TASK_B: %s", TASK_B_NAME)
    attrs = TaskAttributes(
        instruction="Summarize insights from previous analysis",
        input=TASK_A_NAME,
        tools=None,
        enable_human_tool=True,
    )
    task = Task(task_name=TASK_B_NAME, description="Chained summarization task", attributes=attrs)
    task.create()
    logger.info("TASK_B created successfully")
    yield task
    logger.info("Deleting TASK_B: %s", TASK_B_NAME)
    task.delete(force=True)
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(TASK_B_NAME))
    logger.info("TASK_B deleted successfully")

# -----------------------------------------------------------------------------
# Positive Tests
# -----------------------------------------------------------------------------

def test_3100_task_creation(task_a):
    logger.info("Verifying TASK_A creation")
    logger.info("Task Name       : %s", task_a.task_name)
    logger.info("Task Description: %s", task_a.description)
    logger.info("Task Attributes:")
    logger.info("  enable_human_tool = %s", task_a.attributes.enable_human_tool)
    logger.info("  tools             = %s", task_a.attributes.tools)
    assert task_a.task_name == TASK_A_NAME
    assert task_a.description == "Primary analysis task"
    assert task_a.attributes.enable_human_tool is False
    assert task_a.attributes.tools == ["MOVIE_SQL_TOOL"]

def test_3101_task_chaining(task_b):
    logger.info("Verifying TASK_B chaining")
    logger.info("TASK_B attributes:")
    logger.info("  input              = %s", task_b.attributes.input)
    logger.info("  enable_human_tool  = %s", task_b.attributes.enable_human_tool)
    assert task_b.attributes.input == TASK_A_NAME
    assert task_b.attributes.enable_human_tool is True

def test_3102_fetch_task(task_a):
    logger.info("Fetching TASK_A")
    fetched = Task.fetch(TASK_A_NAME)
    logger.info("Fetched task details:")
    logger.info("  task_name  = %s", fetched.task_name)
    logger.info("  attributes = %s", fetched.attributes)
    logger.info("Original task attributes:")
    logger.info("  attributes = %s", task_a.attributes)
    assert fetched.task_name == TASK_A_NAME
    assert fetched.attributes == task_a.attributes

def test_3103_list_tasks_with_regex():
    logger.info("Listing tasks with regex")
    tasks = list(Task.list(f"{BASE}.*"))
    names = sorted(t.task_name for t in tasks)
    logger.info("Tasks returned (sorted):")
    for name in names:
        logger.info("  - %s", name)
    assert TASK_A_NAME in names
    assert TASK_B_NAME in names


def test_3104_disable_enable_task(task_b):
    logger.info("Disabling TASK_B: %s", task_b.task_name)
    task_b.disable()

    status = get_task_status(task_b.task_name)
    logger.info("DB status after disable: %s", status)
    assert status == "DISABLED"

    logger.info("Enabling TASK_B: %s", task_b.task_name)
    task_b.enable()

    status = get_task_status(task_b.task_name)
    logger.info("DB status after enable: %s", status)
    assert status == "ENABLED"

# -----------------------------------------------------------------------------
# Negative / Edge Case Tests with Error Code Asserts
# -----------------------------------------------------------------------------

def test_3105_set_single_attribute_invalid(task_b):
    logger.info("Setting invalid single attribute for TASK_B")
    expect_oracle_error("ORA-20051", lambda: task_b.set_attribute("description", "New Desc"))

def test_3110_fetch_non_existent_task():
    name = f"{BASE}_NO_SUCH_TASK"
    logger.info("Fetching non-existent task: %s", name)
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(name))

def test_3111_duplicate_task_creation_fails(task_a):
    logger.info("Creating duplicate TASK_A without replace")
    logger.info("  task_name = %s", task_a.task_name)
    dup = Task(
        task_name=task_a.task_name,
        description="Duplicate task",
        attributes=task_a.attributes,
    )
    expect_oracle_error("ORA-20051", lambda: dup.create(replace=False))

def test_3113_set_invalid_attribute(task_a):
    logger.info("Setting invalid attribute for TASK_A")
    logger.info("  attribute = unknown_attribute")
    expect_oracle_error("ORA-20051", lambda: task_a.set_attribute("unknown_attribute", "value"))

def test_3114_invalid_regex_pattern():
    logger.info("Listing tasks with invalid regex")
    expect_oracle_error("ORA-12726", lambda: list(Task.list("[INVALID_REGEX")))

def test_3115_delete_disabled_task_without_force():
    task_name = f"{BASE}_TEMP_DELETE"
    logger.info("Creating and deleting disabled task: %s", task_name)
    attrs = TaskAttributes(instruction="Temporary task", tools=None)
    task = Task(task_name=task_name, description="Temp task", attributes=attrs)
    task.create()
    task.disable()
    # DB verification: task is DISABLED
    status = get_task_status(task_name)
    logger.info("Task status before delete: %s", status)
    assert status == "DISABLED"
    task.delete(force=False)
    # DB verification: task removed
    status = get_task_status(task_name)
    logger.info("Task status after delete: %s", status)
    assert status is None
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(task_name))


def test_3116_missing_instruction():
    task_name = f"{BASE}_NO_INSTRUCTION"
    logger.info("Creating task with missing instruction: %s", task_name)
    attrs = TaskAttributes(instruction="", tools=None)
    task = Task(task_name=task_name, attributes=attrs)
    expect_oracle_error("ORA-20051", lambda: task.create())

def test_3117_delete_enabled_task_without_force_succeeds():
    task_name = f"{BASE}_FORCE_DELETE_TEST"
    logger.info("Creating and deleting enabled task: %s", task_name)
    attrs = TaskAttributes(instruction="Delete force test", tools=None)
    task = Task(task_name=task_name, attributes=attrs)
    task.create(enabled=True)
    # DB verification: task is ENABLED
    status = get_task_status(task_name)
    logger.info("Task status before delete: %s", status)
    assert status == "ENABLED"
    task.delete(force=False)
    # DB verification: task removed
    status = get_task_status(task_name)
    logger.info("Task status after delete: %s", status)
    assert status is None
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(task_name))


def test_3118_delete_disabled_task_with_force_succeeds():
    task_name = f"{BASE}_DISABLED_CREATE"
    logger.info("Deleting initially disabled task: %s", task_name)
    attrs = TaskAttributes(instruction="Initially disabled task", tools=None)
    task = Task(task_name=task_name, attributes=attrs)
    task.create(enabled=False)
    # DB verification: task is DISABLED
    status = get_task_status(task_name)
    logger.info("Task status before delete: %s", status)
    assert status == "DISABLED"
    task.delete(force=True)
    # DB verification: task removed
    status = get_task_status(task_name)
    logger.info("Task status after delete: %s", status)
    assert status is None
    expect_oracle_error("NOT_FOUND", lambda: Task.fetch(task_name))
