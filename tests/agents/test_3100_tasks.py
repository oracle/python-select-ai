# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3100 - Module for testing select_ai agent tasks
"""

import uuid

import pytest
import select_ai
from select_ai.agent import Task, TaskAttributes

PYSAI_3100_TASK_NAME = f"PYSAI_3100_{uuid.uuid4().hex.upper()}"
PYSAI_3100_SQL_TASK_DESCRIPTION = "PYSAI_3100_SQL_TASK_DESCRIPTION"


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
def task(task_attributes):
    task = Task(
        task_name=PYSAI_3100_TASK_NAME,
        description=PYSAI_3100_SQL_TASK_DESCRIPTION,
        attributes=task_attributes,
    )
    task.create()
    yield task
    task.delete(force=True)


def test_3100(task, task_attributes):
    """simple task creation"""
    assert task.task_name == PYSAI_3100_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3100_SQL_TASK_DESCRIPTION


@pytest.mark.parametrize("task_name_pattern", [None, "^PYSAI_3100_"])
def test_3101(task_name_pattern):
    """task list"""
    if task_name_pattern:
        tasks = list(select_ai.agent.Task.list(task_name_pattern))
    else:
        tasks = list(select_ai.agent.Task.list())
    task_names = set(task.task_name for task in tasks)
    task_descriptions = set(task.description for task in tasks)
    assert PYSAI_3100_TASK_NAME in task_names
    assert PYSAI_3100_SQL_TASK_DESCRIPTION in task_descriptions


def test_3102(task_attributes):
    """task fetch"""
    task = select_ai.agent.Task.fetch(PYSAI_3100_TASK_NAME)
    assert task.task_name == PYSAI_3100_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3100_SQL_TASK_DESCRIPTION
