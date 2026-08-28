# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Typed access to the current user's Select AI Agent history views."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    AsyncGenerator,
    Iterator,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

import oracledb

from select_ai._abc import SelectAIDataClass
from select_ai.agent.sql import (
    LIST_USER_AI_AGENT_TASK_HISTORY,
    LIST_USER_AI_AGENT_TEAM_HISTORY,
    LIST_USER_AI_AGENT_TOOL_HISTORY,
)
from select_ai.db import async_cursor, cursor


@dataclass
class TeamHistoryEvent(SelectAIDataClass):
    """One row from ``USER_AI_AGENT_TEAM_HISTORY``."""

    team_exec_id: str
    team_name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    conversation_id: Optional[str] = None
    params: Optional[str] = None


@dataclass
class TaskHistoryEvent(SelectAIDataClass):
    """One row from ``USER_AI_AGENT_TASK_HISTORY``."""

    team_exec_id: str
    team_name: str
    task_order: Optional[int]
    agent_name: str
    task_name: Optional[str]
    conversation_params: Optional[str]
    input: Optional[str]
    result: Optional[str]
    state: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]


@dataclass
class ToolHistoryEvent(SelectAIDataClass):
    """One row from ``USER_AI_AGENT_TOOL_HISTORY``."""

    invocation_id: int
    team_exec_id: str
    task_order: Optional[int]
    tool_name: Optional[str]
    agent_name: Optional[str]
    task_name: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    input: Optional[Any]
    output: Optional[Any]
    tool_output: Optional[str]

    def __post_init__(self):
        super().__post_init__()
        self.input = _load_json(self.input)
        self.output = _load_json(self.output)


HistoryEvent = TypeVar("HistoryEvent", bound=SelectAIDataClass)


def _load_json(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _validate_limit(limit: Optional[int]) -> None:
    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise ValueError("'limit' must be a positive integer or None")


def _read_lobs(row: Sequence[object]) -> tuple:
    return tuple(
        value.read() if isinstance(value, oracledb.LOB) else value
        for value in row
    )


async def _async_read_lobs(row: Sequence[object]) -> tuple:
    values = []
    for value in row:
        if isinstance(value, oracledb.AsyncLOB):
            value = await value.read()
        values.append(value)
    return tuple(values)


def _events(
    query: str,
    event_type: Type[HistoryEvent],
    parameters: dict,
    limit: Optional[int],
) -> Iterator[HistoryEvent]:
    _validate_limit(limit)
    with cursor() as cr:
        cr.execute(query, parameters)
        count = 0
        for row in cr:
            yield event_type(*_read_lobs(row))
            count += 1
            if limit is not None and count >= limit:
                break


async def _async_events(
    query: str,
    event_type: Type[HistoryEvent],
    parameters: dict,
    limit: Optional[int],
) -> AsyncGenerator[HistoryEvent, None]:
    _validate_limit(limit)
    async with async_cursor() as cr:
        await cr.execute(query, parameters)
        count = 0
        async for row in cr:
            yield event_type(*await _async_read_lobs(row))
            count += 1
            if limit is not None and count >= limit:
                break


class TeamHistory:
    """Read runs from ``USER_AI_AGENT_TEAM_HISTORY``."""

    @classmethod
    def list(
        cls,
        team_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[TeamHistoryEvent]:
        """Yield team runs ordered from newest to oldest."""
        yield from _events(
            LIST_USER_AI_AGENT_TEAM_HISTORY,
            TeamHistoryEvent,
            {"team_name": team_name, "team_exec_id": team_exec_id},
            limit,
        )


class TaskHistory:
    """Read task runs from ``USER_AI_AGENT_TASK_HISTORY``."""

    @classmethod
    def list(
        cls,
        team_name: Optional[str] = None,
        task_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[TaskHistoryEvent]:
        """Yield task runs ordered from newest to oldest."""
        yield from _events(
            LIST_USER_AI_AGENT_TASK_HISTORY,
            TaskHistoryEvent,
            {
                "team_name": team_name,
                "task_name": task_name,
                "agent_name": agent_name,
                "team_exec_id": team_exec_id,
            },
            limit,
        )


class ToolHistory:
    """Read tool calls from ``USER_AI_AGENT_TOOL_HISTORY``."""

    @classmethod
    def list(
        cls,
        tool_name: Optional[str] = None,
        task_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[ToolHistoryEvent]:
        """Yield tool calls ordered from newest to oldest."""
        yield from _events(
            LIST_USER_AI_AGENT_TOOL_HISTORY,
            ToolHistoryEvent,
            {
                "tool_name": tool_name,
                "task_name": task_name,
                "agent_name": agent_name,
                "team_exec_id": team_exec_id,
            },
            limit,
        )


class AsyncTeamHistory:
    """Asynchronously read runs from ``USER_AI_AGENT_TEAM_HISTORY``."""

    @classmethod
    async def list(
        cls,
        team_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncGenerator[TeamHistoryEvent, None]:
        """Yield team runs ordered from newest to oldest."""
        async for event in _async_events(
            LIST_USER_AI_AGENT_TEAM_HISTORY,
            TeamHistoryEvent,
            {"team_name": team_name, "team_exec_id": team_exec_id},
            limit,
        ):
            yield event


class AsyncTaskHistory:
    """Asynchronously read task runs from ``USER_AI_AGENT_TASK_HISTORY``."""

    @classmethod
    async def list(
        cls,
        team_name: Optional[str] = None,
        task_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncGenerator[TaskHistoryEvent, None]:
        """Yield task runs ordered from newest to oldest."""
        async for event in _async_events(
            LIST_USER_AI_AGENT_TASK_HISTORY,
            TaskHistoryEvent,
            {
                "team_name": team_name,
                "task_name": task_name,
                "agent_name": agent_name,
                "team_exec_id": team_exec_id,
            },
            limit,
        ):
            yield event


class AsyncToolHistory:
    """Asynchronously read tool calls from ``USER_AI_AGENT_TOOL_HISTORY``."""

    @classmethod
    async def list(
        cls,
        tool_name: Optional[str] = None,
        task_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        team_exec_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncGenerator[ToolHistoryEvent, None]:
        """Yield tool calls ordered from newest to oldest."""
        async for event in _async_events(
            LIST_USER_AI_AGENT_TOOL_HISTORY,
            ToolHistoryEvent,
            {
                "tool_name": tool_name,
                "task_name": task_name,
                "agent_name": agent_name,
                "team_exec_id": team_exec_id,
            },
            limit,
        ):
            yield event
