# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import datetime
import json
from dataclasses import dataclass
from typing import AsyncGenerator, Iterator, Optional

import oracledb

from select_ai._abc import SelectAIDataClass
from select_ai.db import async_cursor, cursor
from select_ai.errors import ConversationNotFoundError
from select_ai.sql import (
    GET_USER_CONVERSATION_ATTRIBUTES,
    LIST_USER_CONVERSATIONS,
)

__all__ = ["AsyncConversation", "Conversation", "ConversationAttributes"]


@dataclass
class ConversationAttributes(SelectAIDataClass):
    """Conversation Attributes

    :param str title: Conversation Title
    :param str description: Description of the conversation topic
    :param datetime.timedelta retention_days: The number of days the conversation
     will be stored in the database from its creation date. If value is 0, the
     conversation will not be removed unless it is manually deleted by
     delete
    :param int conversation_length: Number of prompts to store for this
     conversation

    """

    title: Optional[str] = "New Conversation"
    description: Optional[str] = None
    retention_days: Optional[datetime.timedelta] = datetime.timedelta(days=7)
    conversation_length: Optional[int] = 10

    def json(self, exclude_null=True):
        attributes = {}
        for k, v in self.dict(exclude_null=exclude_null).items():
            if isinstance(v, datetime.timedelta):
                attributes[k] = v.days
            else:
                attributes[k] = v
        return json.dumps(attributes)


class _BaseConversation:

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        attributes: Optional[ConversationAttributes] = None,
    ):
        self.conversation_id = conversation_id
        self.attributes = attributes

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(conversation_id={self.conversation_id}, "
            f"attributes={self.attributes})"
        )


class Conversation(_BaseConversation):
    """Conversation class can be used to create, update and delete
    conversations in the database

    Typical usage is to combine this conversation object with an AI
    Profile.chat_session() to have context-aware conversations with
    the LLM provider

    :param str conversation_id: Conversation ID
    :param ConversationAttributes attributes: Conversation attributes

    """

    def create(self) -> str:
        """Creates a new conversation and returns the conversation_id
        to be used in context-aware conversations with LLMs

        :return: conversation_id
        """
        with cursor() as cr:
            self.conversation_id = cr.callfunc(
                "DBMS_CLOUD_AI.CREATE_CONVERSATION",
                oracledb.DB_TYPE_VARCHAR,
                keyword_parameters={"attributes": self.attributes.json()},
            )
        return self.conversation_id

    def delete(self, force: bool = False):
        """Drops the conversation"""
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DROP_CONVERSATION",
                keyword_parameters={
                    "conversation_id": self.conversation_id,
                    "force": force,
                },
            )

    @classmethod
    def fetch(cls, conversation_id: str) -> "Conversation":
        """Fetch conversation attributes from the database
        and build a proxy object

        :param str conversation_id: Conversation ID

        """
        conversation = cls(conversation_id=conversation_id)
        conversation.attributes = conversation.get_attributes()
        return conversation

    def set_attributes(self, attributes: ConversationAttributes):
        """Updates the attributes of the conversation in the database"""
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_CONVERSATION",
                keyword_parameters={
                    "conversation_id": self.conversation_id,
                    "attributes": attributes.json(),
                },
            )
        self.attributes = self.get_attributes()

    def get_attributes(self) -> ConversationAttributes:
        """Get attributes of the conversation from the database"""
        with cursor() as cr:
            cr.execute(
                GET_USER_CONVERSATION_ATTRIBUTES,
                conversation_id=self.conversation_id,
            )
            attributes = cr.fetchone()
            if attributes:
                conversation_title = attributes[0]
                if attributes[1]:
                    description = attributes[1].read()  # Oracle.LOB
                else:
                    description = None
                retention_days = attributes[2]
                return ConversationAttributes(
                    title=conversation_title,
                    description=description,
                    retention_days=retention_days,
                )
            else:
                raise ConversationNotFoundError(
                    conversation_id=self.conversation_id
                )

    @classmethod
    def list(cls) -> Iterator["Conversation"]:
        """List all conversations

        :return: Iterator[VectorIndex]
        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_CONVERSATIONS,
            )
            for row in cr.fetchall():
                conversation_id = row[0]
                conversation_title = row[1]
                if row[2]:
                    description = row[2].read()  # Oracle.LOB
                else:
                    description = None
                retention_days = row[3]
                attributes = ConversationAttributes(
                    title=conversation_title,
                    description=description,
                    retention_days=retention_days,
                )
                yield cls(
                    attributes=attributes, conversation_id=conversation_id
                )


class AsyncConversation(_BaseConversation):
    """AsyncConversation class can be used to create, update and delete
    conversations in the database in an async manner

    Typical usage is to combine this conversation object with an
    AsyncProfile.chat_session() to have context-aware conversations

    :param str conversation_id: Conversation ID
    :param ConversationAttributes attributes: Conversation attributes

    """

    async def create(self) -> str:
        """Creates a new conversation and returns the conversation_id
        to be used in context-aware conversations with LLMs

        :return: conversation_id
        """
        async with async_cursor() as cr:
            self.conversation_id = await cr.callfunc(
                "DBMS_CLOUD_AI.CREATE_CONVERSATION",
                oracledb.DB_TYPE_VARCHAR,
                keyword_parameters={"attributes": self.attributes.json()},
            )
        return self.conversation_id

    async def delete(self, force: bool = False):
        """Delete the conversation"""
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DROP_CONVERSATION",
                keyword_parameters={
                    "conversation_id": self.conversation_id,
                    "force": force,
                },
            )

    @classmethod
    async def fetch(cls, conversation_id: str) -> "AsyncConversation":
        """Fetch conversation attributes from the database"""
        conversation = cls(conversation_id=conversation_id)
        conversation.attributes = await conversation.get_attributes()
        return conversation

    async def set_attributes(self, attributes: ConversationAttributes):
        """Updates the attributes of the conversation"""
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_CONVERSATION",
                keyword_parameters={
                    "conversation_id": self.conversation_id,
                    "attributes": attributes.json(),
                },
            )
        self.attributes = await self.get_attributes()

    async def get_attributes(self) -> ConversationAttributes:
        """Get attributes of the conversation from the database"""
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_CONVERSATION_ATTRIBUTES,
                conversation_id=self.conversation_id,
            )
            attributes = await cr.fetchone()
            if attributes:
                conversation_title = attributes[0]
                if attributes[1]:
                    description = await attributes[1].read()  # Oracle.AsyncLOB
                else:
                    description = None
                retention_days = attributes[2]
                return ConversationAttributes(
                    title=conversation_title,
                    description=description,
                    retention_days=retention_days,
                )
            else:
                raise ConversationNotFoundError(
                    conversation_id=self.conversation_id
                )

    @classmethod
    async def list(cls) -> AsyncGenerator["AsyncConversation", None]:
        """List all conversations

        :return: Iterator[VectorIndex]
        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_CONVERSATIONS,
            )
            rows = await cr.fetchall()
            for row in rows:
                conversation_id = row[0]
                conversation_title = row[1]
                if row[2]:
                    description = await row[2].read()  # Oracle.AsyncLOB
                else:
                    description = None
                retention_days = row[3]
                attributes = ConversationAttributes(
                    title=conversation_title,
                    description=description,
                    retention_days=retention_days,
                )
                yield cls(
                    attributes=attributes, conversation_id=conversation_id
                )
