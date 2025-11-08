# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3500 - Module for testing select_ai agent async tasks
"""

import uuid

import pytest
import select_ai
from select_ai.agent import AsyncTask, TaskAttributes

PYSAI_3500_TASK_NAME = f"PYSAI_3500_TASK_{uuid.uuid4().hex.upper()}"
PYSAI_3500_SQL_TASK_DESCRIPTION = "PYSAI_3500_SQL_TASK_DESCRIPTION"


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
        task_name=PYSAI_3500_TASK_NAME,
        description=PYSAI_3500_SQL_TASK_DESCRIPTION,
        attributes=task_attributes,
    )
    await task.create()
    yield task
    await task.delete(force=True)


async def test_3500(task, task_attributes):
    """simple task creation"""
    assert task.task_name == PYSAI_3500_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3500_SQL_TASK_DESCRIPTION


@pytest.mark.parametrize("task_name_pattern", [None, "^PYSAI_3500_"])
async def test_3501(task_name_pattern):
    """task list"""
    if task_name_pattern:
        tasks = [
            task
            async for task in select_ai.agent.AsyncTask.list(task_name_pattern)
        ]
    else:
        tasks = [task async for task in select_ai.agent.AsyncTask.list()]
    task_names = set(task.task_name for task in tasks)
    task_descriptions = set(task.description for task in tasks)
    assert PYSAI_3500_TASK_NAME in task_names
    assert PYSAI_3500_SQL_TASK_DESCRIPTION in task_descriptions


async def test_3502(task_attributes):
    """task fetch"""
    task = await select_ai.agent.AsyncTask.fetch(PYSAI_3500_TASK_NAME)
    assert task.task_name == PYSAI_3500_TASK_NAME
    assert task.attributes == task_attributes
    assert task.description == PYSAI_3500_SQL_TASK_DESCRIPTION
