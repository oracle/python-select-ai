# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1500 - AsyncConversation API tests
"""

import logging
import uuid

import pytest
import select_ai
from oracledb import DatabaseError
from select_ai import AsyncConversation, ConversationAttributes

logger = logging.getLogger(__name__)

CONVERSATION_PREFIX = f"PYSAI_1500_{uuid.uuid4().hex.upper()}"


@pytest.fixture
async def async_conversation_factory():
    created = []

    async def _create(**kwargs):
        logger.info("Creating async conversation with params %s", kwargs)
        attributes = ConversationAttributes(**kwargs)
        conversation = AsyncConversation(attributes=attributes)
        await conversation.create()
        created.append(conversation)
        return conversation

    yield _create

    for conversation in created:
        logger.info(
            "Deleting async conversation %s", conversation.conversation_id
        )
        await conversation.delete(force=True)


@pytest.fixture
async def async_conversation(async_conversation_factory):
    logger.info("Creating default async conversation instance")
    return await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_ACTIVE"
    )


@pytest.mark.anyio
async def test_1500_create_with_title(async_conversation):
    """Create an async conversation with title"""
    logger.info("Validating async conversation creation with title")
    assert async_conversation.conversation_id


@pytest.mark.anyio
async def test_1501_create_with_description(async_conversation_factory):
    """Create an async conversation with title and description"""
    logger.info("Creating async conversation with title and description")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_HISTORY",
        description="LLM's understanding of history of science",
    )
    attributes = await conversation.get_attributes()
    logger.debug("Fetched async conversation attributes: %s", attributes)
    assert attributes.title == f"{CONVERSATION_PREFIX}_HISTORY"
    assert (
        attributes.description == "LLM's understanding of history of science"
    )


@pytest.mark.anyio
async def test_1502_create_without_title(async_conversation_factory):
    """Create an async conversation without providing a title"""
    logger.info("Creating async conversation without explicit title")
    conversation = await async_conversation_factory()
    attributes = await conversation.get_attributes()
    assert attributes.title == "New Conversation"


@pytest.mark.anyio
async def test_1503_create_with_missing_attributes():
    """Missing attributes raise AttributeError"""
    logger.info("Validating missing async attributes raise AttributeError")
    conversation = AsyncConversation(attributes=None)
    with pytest.raises(AttributeError):
        await conversation.create()


@pytest.mark.anyio
async def test_1504_get_attributes(async_conversation):
    """Fetch async conversation attributes"""
    logger.info(
        "Fetching attributes for async conversation %s",
        async_conversation.conversation_id,
    )
    attributes = await async_conversation.get_attributes()
    assert attributes.title == f"{CONVERSATION_PREFIX}_ACTIVE"
    assert attributes.description is None


@pytest.mark.anyio
async def test_1505_set_attributes(async_conversation):
    """Update async conversation attributes"""
    logger.info(
        "Updating async conversation attributes for %s",
        async_conversation.conversation_id,
    )
    updated = ConversationAttributes(
        title=f"{CONVERSATION_PREFIX}_UPDATED",
        description="Updated Description",
    )
    await async_conversation.set_attributes(updated)
    attributes = await async_conversation.get_attributes()
    assert attributes.title == f"{CONVERSATION_PREFIX}_UPDATED"
    assert attributes.description == "Updated Description"


@pytest.mark.anyio
async def test_1506_set_attributes_with_none(async_conversation):
    """Setting empty attributes raises AttributeError"""
    logger.info(
        "Validating async set_attributes(None) raises AttributeError for %s",
        async_conversation.conversation_id,
    )
    with pytest.raises(
        AttributeError, match="'NoneType' object has no attribute 'json'"
    ):
        await async_conversation.set_attributes(None)


@pytest.mark.anyio
async def test_1507_delete_conversation(async_conversation_factory):
    """Delete async conversation and validate removal"""
    logger.info("Creating async conversation to validate deletion")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_DELETE"
    )
    await conversation.delete(force=True)
    with pytest.raises(select_ai.errors.ConversationNotFoundError):
        await conversation.get_attributes()


@pytest.mark.anyio
async def test_1508_delete_twice(async_conversation_factory):
    """Deleting an already deleted async conversation raises DatabaseError"""
    logger.info(
        "Validating double deletion raises DatabaseError for async conversation"
    )
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_DELETE_TWICE"
    )
    await conversation.delete(force=True)
    with pytest.raises(DatabaseError) as exc_info:
        await conversation.delete()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "does not exist" in error.message


@pytest.mark.anyio
async def test_1509_list_contains_created_conversation(async_conversation):
    """Async conversation list contains the created conversation"""
    logger.info(
        "Ensuring async conversation list includes created conversation"
    )
    ids = {item.conversation_id async for item in AsyncConversation.list()}
    assert async_conversation.conversation_id in ids


@pytest.mark.anyio
async def test_1510_multiple_conversations_have_unique_ids(
    async_conversation_factory,
):
    """Multiple async conversations produce unique identifiers"""
    logger.info("Creating multiple async conversations to verify unique IDs")
    titles = [
        f"{CONVERSATION_PREFIX}_AI",
        f"{CONVERSATION_PREFIX}_DB",
        f"{CONVERSATION_PREFIX}_MATH",
    ]
    conversations = [
        await async_conversation_factory(title=title) for title in titles
    ]
    ids = {conversation.conversation_id for conversation in conversations}
    assert len(ids) == len(titles)


@pytest.mark.anyio
async def test_1511_create_with_long_values():
    """Creating async conversation with overly long values fails"""
    logger.info("Validating long attribute values trigger async failure")
    conversation = AsyncConversation(
        attributes=ConversationAttributes(
            title="A" * 255,
            description="B" * 1000,
        )
    )
    with pytest.raises(DatabaseError) as exc_info:
        await conversation.create()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert (
        "Value is too long for conversation attribute - title" in error.message
    )


@pytest.mark.anyio
async def test_1512_set_attributes_with_invalid_id():
    """Updating async conversation with invalid id raises DatabaseError"""
    logger.info(
        "Validating async set_attributes invalid ID raises DatabaseError"
    )
    conversation = AsyncConversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError) as exc_info:
        await conversation.set_attributes(
            ConversationAttributes(title="Invalid")
        )
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "Invalid value for conversation id" in error.message


@pytest.mark.anyio
async def test_1513_delete_with_invalid_id():
    """Deleting async conversation with invalid id raises DatabaseError"""
    logger.info("Validating async delete invalid ID raises DatabaseError")
    conversation = AsyncConversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError) as exc_info:
        await conversation.delete()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "Invalid value for conversation id" in error.message


@pytest.mark.anyio
async def test_1514_get_attributes_with_invalid_id():
    """Fetching attributes for invalid async conversation raises ConversationNotFound"""
    logger.info(
        "Validating async get_attributes with invalid ID raises ConversationNotFound"
    )
    conversation = AsyncConversation(conversation_id="invalid")
    with pytest.raises(
        select_ai.errors.ConversationNotFoundError, match="not found"
    ):
        await conversation.get_attributes()


@pytest.mark.anyio
async def test_1515_get_attributes_for_deleted_conversation(
    async_conversation_factory,
):
    """Fetching attributes after deletion raises ConversationNotFound"""
    logger.info("Validating async get_attributes after deletion raises error")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_TO_DELETE"
    )
    await conversation.delete(force=True)
    with pytest.raises(
        select_ai.errors.ConversationNotFoundError, match="not found"
    ):
        await conversation.get_attributes()


@pytest.mark.anyio
async def test_1516_list_contains_new_conversation(async_conversation_factory):
    """List reflects newly created async conversation"""
    logger.info("Ensuring async list reflects newly created conversation")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_LIST"
    )
    listed = [item async for item in AsyncConversation.list()]
    logger.info("List = %s", listed)
    assert any(
        item.conversation_id == conversation.conversation_id for item in listed
    )


@pytest.mark.anyio
async def test_1517_list_returns_async_conversation_instances():
    """List returns AsyncConversation objects"""
    logger.info(
        "Validating AsyncConversation.list returns AsyncConversation instances"
    )
    listed = [item async for item in AsyncConversation.list()]
    logger.info("List = %s", listed)
    assert all(isinstance(item, AsyncConversation) for item in listed)


@pytest.mark.anyio
async def test_1518_get_attributes_without_description(
    async_conversation_factory,
):
    """Async conversation created without description has None description"""
    logger.info("Creating async conversation without description")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_NO_DESC"
    )
    attributes = await conversation.get_attributes()
    assert attributes.title == f"{CONVERSATION_PREFIX}_NO_DESC"
    assert attributes.description is None


@pytest.mark.anyio
async def test_1519_create_with_description_none(async_conversation_factory):
    """Explicitly setting description to None is allowed"""
    logger.info("Creating async conversation with description explicitly None")
    conversation = await async_conversation_factory(
        title=f"{CONVERSATION_PREFIX}_NONE_DESC",
        description=None,
    )
    attributes = await conversation.get_attributes()
    assert attributes.title == f"{CONVERSATION_PREFIX}_NONE_DESC"
    assert attributes.description is None
