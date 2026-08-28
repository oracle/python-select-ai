# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Oracle Database storage for A2A-to-Oracle conversation mappings."""

from asyncio import Lock
from typing import Optional

import oracledb
from a2a.server.context import ServerCallContext
from a2a.server.owner_resolver import OwnerResolver, resolve_user_scope

import select_ai
from select_ai.db import async_get_connection

_CREATE_TABLE = """
    BEGIN
        EXECUTE IMMEDIATE '
            CREATE TABLE SELECT_AI_A2A_CONTEXTS (
                owner VARCHAR2(512) NOT NULL,
                context_id VARCHAR2(255) NOT NULL,
                conversation_id VARCHAR2(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                CONSTRAINT select_ai_a2a_contexts_pk PRIMARY KEY (owner, context_id)
            )';
        EXECUTE IMMEDIATE '
            COMMENT ON TABLE SELECT_AI_A2A_CONTEXTS
            IS ''Managed by select_ai.a2a.context_store''';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -955 THEN
                RAISE;
            END IF;
    END;
"""


class OracleContextStore:
    """Persist one Oracle conversation for each A2A context."""

    def __init__(
        self,
        owner_resolver: OwnerResolver = resolve_user_scope,
    ) -> None:
        self.owner_resolver = owner_resolver
        self.initialized = False
        self.initialize_lock = Lock()

    async def initialize(self) -> None:
        """Create the context mapping table if it does not already exist."""
        if self.initialized:
            return
        async with self.initialize_lock:
            if self.initialized:
                return
            await self._execute(_CREATE_TABLE)
            self.initialized = True

    async def get_or_create(
        self,
        context_id: str,
        context: ServerCallContext,
        team_name: str,
    ) -> str:
        """Return the Oracle conversation for an A2A context, creating it once."""
        await self.initialize()
        owner = self._owner(context)
        conversation_id = await self._get(owner, context_id)
        if conversation_id:
            return conversation_id

        conversation = select_ai.AsyncConversation(
            attributes=select_ai.ConversationAttributes(
                title=f"A2A {team_name}",
                description=f"A2A context {context_id}",
            )
        )
        conversation_id = await conversation.create()
        try:
            await self._execute(
                """
                    INSERT INTO SELECT_AI_A2A_CONTEXTS (
                        owner, context_id, conversation_id, created_at
                    ) VALUES (
                        :owner, :context_id, :conversation_id, SYSTIMESTAMP
                    )
                """,
                owner=owner,
                context_id=context_id,
                conversation_id=conversation_id,
            )
        except oracledb.DatabaseError as error:
            if error.args[0].code != 1:
                raise
            existing_conversation_id = await self._get(owner, context_id)
            if existing_conversation_id:
                return existing_conversation_id
            raise
        return conversation_id

    async def _get(self, owner: str, context_id: str) -> Optional[str]:
        row = await self._fetchone(
            """
                SELECT conversation_id
                FROM SELECT_AI_A2A_CONTEXTS
                WHERE owner = :owner AND context_id = :context_id
            """,
            owner=owner,
            context_id=context_id,
        )
        return row[0] if row else None

    def _owner(self, context: ServerCallContext) -> str:
        return self.owner_resolver(context) or "anonymous"

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
