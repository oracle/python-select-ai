# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1400 - Conversation API tests
"""

import logging
import uuid

import pytest
import select_ai
from oracledb import DatabaseError
from select_ai import Conversation, ConversationAttributes

logger = logging.getLogger(__name__)

CONVERSATION_PREFIX = f"PYSAI_1400_{uuid.uuid4().hex.upper()}"


@pytest.fixture
def conversation_factory():
    created = []

    def _create(**kwargs):
        logger.info("Creating conversation with params %s", kwargs)
        attributes = ConversationAttributes(**kwargs)
        conv = Conversation(attributes=attributes)
        conv.create()
        created.append(conv)
        return conv

    yield _create

    for conv in created:
        logger.info("Deleting conversation %s", conv.conversation_id)
        conv.delete(force=True)


@pytest.fixture
def conversation(conversation_factory):
    logger.info("Creating default conversation instance")
    return conversation_factory(title=f"{CONVERSATION_PREFIX}_ACTIVE")


def test_1400_create_with_title(conversation):
    """Create a conversation with title"""
    logger.info("Validating conversation creation with title")
    logger.info("Conversation = %s", conversation)
    assert conversation.conversation_id


def test_1401_create_with_description(conversation_factory):
    """Create a conversation with title and description"""
    logger.info("Creating conversation with title and description")
    conv = conversation_factory(
        title=f"{CONVERSATION_PREFIX}_HISTORY",
        description="LLM's understanding of history of science",
    )
    logger.info("Conversation = %s", conv)
    attrs = conv.get_attributes()
    logger.debug("Fetched attributes: %s", attrs)
    assert attrs.title == f"{CONVERSATION_PREFIX}_HISTORY"
    assert attrs.description == "LLM's understanding of history of science"


def test_1402_create_without_title(conversation_factory):
    """Create a conversation without providing a title"""
    logger.info("Creating conversation without explicit title")
    conv = conversation_factory()
    logger.info("Conversation = %s", conv)
    attrs = conv.get_attributes()
    logger.debug("Fetched attributes: %s", attrs)
    assert attrs.title == "New Conversation"


def test_1403_create_with_missing_attributes():
    """Missing attributes raise AttributeError"""
    logger.info("Validating missing attributes raise AttributeError")
    conv = Conversation(attributes=None)
    logger.info("Conversation = %s", conv)
    with pytest.raises(
        AttributeError, match="'NoneType' object has no attribute 'json'"
    ):
        conv.create()


def test_1404_get_attributes(conversation):
    """Fetch conversation attributes"""
    logger.info(
        "Fetching attributes for conversation %s", conversation.conversation_id
    )
    attrs = conversation.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_ACTIVE"
    assert attrs.description is None


def test_1405_set_attributes(conversation):
    """Update conversation attributes"""
    logger.info(
        "Updating conversation attributes for %s", conversation.conversation_id
    )
    updated = ConversationAttributes(
        title=f"{CONVERSATION_PREFIX}_UPDATED",
        description="Updated Description",
    )
    conversation.set_attributes(updated)
    attrs = conversation.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_UPDATED"
    assert attrs.description == "Updated Description"


def test_1406_set_attributes_with_none(conversation):
    """Setting empty attributes raises AttributeError"""
    logger.info(
        "Validating setting None attributes raises AttributeError for %s",
        conversation.conversation_id,
    )
    with pytest.raises(
        AttributeError, match="'NoneType' object has no attribute 'json'"
    ):
        conversation.set_attributes(None)


def test_1407_delete_conversation(conversation_factory):
    """Delete conversation and validate removal"""
    logger.info("Creating conversation to validate deletion")
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_DELETE")
    conv.delete(force=True)
    with pytest.raises(select_ai.errors.ConversationNotFoundError):
        conv.get_attributes()


def test_1408_delete_twice(conversation_factory):
    """Deleting an already deleted conversation raises DatabaseError"""
    logger.info("Validating double deletion raises DatabaseError")
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_DELETE_TWICE")
    conv.delete(force=True)
    with pytest.raises(DatabaseError) as exc_info:
        conv.delete()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "does not exist" in error.message


def test_1409_list_contains_created_conversation(conversation):
    """Conversation list contains the created conversation"""
    logger.info("Ensuring conversation list includes created conversation")
    conversation_ids = {item.conversation_id for item in Conversation.list()}
    assert conversation.conversation_id in conversation_ids


def test_1410_multiple_conversations_have_unique_ids(conversation_factory):
    """Multiple conversations produce unique identifiers"""
    logger.info("Creating multiple conversations to verify unique IDs")
    titles = [
        f"{CONVERSATION_PREFIX}_AI",
        f"{CONVERSATION_PREFIX}_DB",
        f"{CONVERSATION_PREFIX}_MATH",
    ]
    conversations = [conversation_factory(title=title) for title in titles]
    ids = {conv.conversation_id for conv in conversations}
    assert len(ids) == len(titles)


def test_1411_create_with_long_values():
    """Creating conversation with overly long values fails"""
    logger.info("Validating long attribute values trigger failure")
    conv = Conversation(
        attributes=ConversationAttributes(
            title="A" * 255,
            description="B" * 1000,
        )
    )
    with pytest.raises(DatabaseError) as exc_info:
        conv.create()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert (
        "Value is too long for conversation attribute - title" in error.message
    )


def test_1412_set_attributes_with_invalid_id():
    """Updating conversation with invalid id raises DatabaseError"""
    logger.info(
        "Validating set_attributes with invalid ID raises DatabaseError"
    )
    conv = Conversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError) as exc_info:
        conv.set_attributes(ConversationAttributes(title="Invalid"))
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "Invalid value for conversation id" in error.message


def test_1413_delete_with_invalid_id():
    """Deleting conversation with invalid id raises DatabaseError"""
    logger.info("Validating delete with invalid ID raises DatabaseError")
    conv = Conversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError) as exc_info:
        conv.delete()
    (error,) = exc_info.value.args
    logger.debug("Error code: %s", error.code)
    logger.debug("Error message:\n%s", error.message)
    assert error.code == 20050
    assert "Invalid value for conversation id" in error.message


def test_1414_get_attributes_with_invalid_id():
    """Fetching attributes for invalid conversation raises ConversationNotFound"""
    logger.info(
        "Validating get_attributes with invalid ID raises ConversationNotFound"
    )
    conv = Conversation(conversation_id="invalid")
    with pytest.raises(
        select_ai.errors.ConversationNotFoundError, match="not found"
    ):
        conv.get_attributes()


def test_1415_get_attributes_for_deleted_conversation(conversation_factory):
    """Fetching attributes after deletion raises ConversationNotFound"""
    logger.info("Validating get_attributes after deletion raises error")
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_TO_DELETE")
    conv.delete(force=True)
    with pytest.raises(
        select_ai.errors.ConversationNotFoundError, match="not found"
    ):
        conv.get_attributes()


def test_1416_list_contains_new_conversation(conversation_factory):
    """List reflects newly created conversation"""
    logger.info("Ensuring list reflects newly created conversation")
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_LIST")
    listed = list(Conversation.list())
    logger.info("List = %s", listed)
    assert any(item.conversation_id == conv.conversation_id for item in listed)


def test_1417_list_returns_conversation_instances():
    """List returns Conversation objects"""
    logger.info("Validating Conversation.list returns Conversation instances")
    listed = list(Conversation.list())
    logger.info("List = %s", listed)
    assert all(isinstance(item, Conversation) for item in listed)


def test_1418_get_attributes_without_description(conversation_factory):
    """Conversation created without description has None description"""
    logger.info("Creating conversation without description")
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_NO_DESC")
    attrs = conv.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_NO_DESC"
    assert attrs.description is None


def test_1419_create_with_description_none(conversation_factory):
    """Explicitly setting description to None is allowed"""
    logger.info("Creating conversation with description explicitly None")
    conv = conversation_factory(
        title=f"{CONVERSATION_PREFIX}_NONE_DESC",
        description=None,
    )
    attrs = conv.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_NONE_DESC"
    assert attrs.description is None
