# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Oracle Database implementation of the A2A TaskStore interface."""

from __future__ import annotations

from asyncio import Lock
from typing import Optional

from a2a.server.context import ServerCallContext
from a2a.server.owner_resolver import OwnerResolver, resolve_user_scope
from a2a.server.tasks.task_store import TaskStore
from a2a.types import a2a_pb2
from a2a.types.a2a_pb2 import Task
from a2a.utils.constants import DEFAULT_LIST_TASKS_PAGE_SIZE
from a2a.utils.errors import InvalidParamsError
from a2a.utils.task import decode_page_token, encode_page_token
from google.protobuf.json_format import MessageToJson, Parse, ParseDict

from select_ai.db import async_get_connection

_CREATE_TABLE = """
    BEGIN
        EXECUTE IMMEDIATE '
            CREATE TABLE SELECT_AI_A2A_TASKS (
                owner VARCHAR2(512) NOT NULL,
                task_id VARCHAR2(255) NOT NULL,
                context_id VARCHAR2(255),
                task_json CLOB NOT NULL CHECK (task_json IS JSON),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                CONSTRAINT select_ai_a2a_tasks_pk PRIMARY KEY (owner, task_id)
            )';
        EXECUTE IMMEDIATE '
            COMMENT ON TABLE SELECT_AI_A2A_TASKS
            IS ''Managed by select_ai.a2a.task_store''';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -955 THEN
                RAISE;
            END IF;
    END;
"""


class OracleTaskStore(TaskStore):
    """Persist A2A tasks in Oracle Database using Select AI's connection pool."""

    def __init__(
        self,
        owner_resolver: OwnerResolver = resolve_user_scope,
    ) -> None:
        self.owner_resolver = owner_resolver
        self.initialized = False
        self.initialize_lock = Lock()

    async def initialize(self) -> None:
        """Create the task table if it does not already exist."""
        if self.initialized:
            return
        async with self.initialize_lock:
            if self.initialized:
                return
            await self._execute(_CREATE_TABLE)
            self.initialized = True

    async def save(self, task: Task, context: ServerCallContext) -> None:
        """Insert or update a task for its resolved owner."""
        await self.initialize()
        await self._execute(
            """
                MERGE INTO SELECT_AI_A2A_TASKS target
                USING (
                    SELECT :owner AS owner, :task_id AS task_id FROM dual
                ) source
                ON (target.owner = source.owner AND target.task_id = source.task_id)
                WHEN MATCHED THEN UPDATE SET
                    context_id = :context_id,
                    task_json = :task_json,
                    updated_at = SYSTIMESTAMP
                WHEN NOT MATCHED THEN INSERT (
                    owner, task_id, context_id, task_json, updated_at
                ) VALUES (
                    :owner, :task_id, :context_id, :task_json, SYSTIMESTAMP
                )
            """,
            owner=self._owner(context),
            task_id=task.id,
            context_id=task.context_id,
            task_json=MessageToJson(task),
        )

    async def get(
        self,
        task_id: str,
        context: ServerCallContext,
    ) -> Optional[Task]:
        """Return a task by ID for its resolved owner."""
        await self.initialize()
        row = await self._fetchone(
            """
                SELECT task_json
                FROM SELECT_AI_A2A_TASKS
                WHERE owner = :owner AND task_id = :task_id
            """,
            owner=self._owner(context),
            task_id=task_id,
        )
        if row is None:
            return None
        return await self._task_from_json(row[0])

    async def list(
        self,
        params: a2a_pb2.ListTasksRequest,
        context: ServerCallContext,
    ) -> a2a_pb2.ListTasksResponse:
        """Return filtered, paginated tasks for the resolved owner."""
        await self.initialize()
        rows = await self._fetchall(
            """
                SELECT task_json
                FROM SELECT_AI_A2A_TASKS
                WHERE owner = :owner
                  AND (
                      :context_id IS NULL OR context_id = :context_id
                  )
                  AND (
                      :status IS NULL OR
                      JSON_VALUE(task_json, '$.status.state') = :status
                  )
                  AND (
                      :status_timestamp_after IS NULL OR
                      JSON_VALUE(task_json, '$.status.timestamp')
                          >= :status_timestamp_after
                  )
                ORDER BY updated_at DESC, task_id DESC
            """,
            owner=self._owner(context),
            **self._list_query_parameters(params),
        )
        tasks = [await self._task_from_json(row[0]) for row in rows]
        total_size = len(tasks)
        start_index = self._page_start_index(tasks, params.page_token)
        page_size = params.page_size or DEFAULT_LIST_TASKS_PAGE_SIZE
        end_index = start_index + page_size
        page = tasks[start_index:end_index]
        next_page_token = (
            encode_page_token(tasks[end_index].id)
            if end_index < total_size
            else None
        )
        return a2a_pb2.ListTasksResponse(
            tasks=page,
            total_size=total_size,
            page_size=page_size,
            next_page_token=next_page_token,
        )

    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        """Delete a task by ID for its resolved owner."""
        await self.initialize()
        await self._execute(
            """
                DELETE FROM SELECT_AI_A2A_TASKS
                WHERE owner = :owner AND task_id = :task_id
            """,
            owner=self._owner(context),
            task_id=task_id,
        )

    @staticmethod
    def _list_query_parameters(
        params: a2a_pb2.ListTasksRequest,
    ) -> dict[str, str | None]:
        """Convert protobuf list filters to Oracle query parameters."""
        status = None
        if params.status:
            try:
                status = a2a_pb2.TaskState.Name(params.status)
            except ValueError:
                # An unknown enum value cannot match a stored protobuf JSON
                # enum name, which preserves the old empty-result behavior.
                status = "__UNKNOWN_TASK_STATE__"
        timestamp_after = (
            params.status_timestamp_after.ToJsonString()
            if params.HasField("status_timestamp_after")
            else None
        )
        return {
            "context_id": params.context_id or None,
            "status": status,
            "status_timestamp_after": timestamp_after,
        }

    def _owner(self, context: ServerCallContext) -> str:
        return self.owner_resolver(context) or "anonymous"

    @staticmethod
    def _page_start_index(tasks: list[Task], page_token: str) -> int:
        if not page_token:
            return 0
        task_id = decode_page_token(page_token)
        for index, task in enumerate(tasks):
            if task.id == task_id:
                return index
        raise InvalidParamsError(f"Invalid page token: {page_token}")

    @staticmethod
    async def _task_from_json(value) -> Task:
        if hasattr(value, "read"):
            value = await value.read()
        task = Task()
        if isinstance(value, dict):
            ParseDict(value, task)
        else:
            Parse(value, task)
        return task

    @staticmethod
    async def _execute(statement: str, **parameters) -> None:
        async with async_get_connection() as connection:
            cursor = connection.cursor()
            try:
                await cursor.execute(statement, **parameters)
                await connection.commit()
            finally:
                cursor.close()

    @staticmethod
    async def _fetchone(statement: str, **parameters):
        async with async_get_connection() as connection:
            cursor = connection.cursor()
            try:
                await cursor.execute(statement, **parameters)
                return await cursor.fetchone()
            finally:
                cursor.close()

    @staticmethod
    async def _fetchall(statement: str, **parameters):
        async with async_get_connection() as connection:
            cursor = connection.cursor()
            try:
                await cursor.execute(statement, **parameters)
                return await cursor.fetchall()
            finally:
                cursor.close()
