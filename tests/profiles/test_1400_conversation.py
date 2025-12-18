# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1400 - Conversation API tests
"""

import uuid

import pytest
import select_ai
from oracledb import DatabaseError
from select_ai import Conversation, ConversationAttributes

CONVERSATION_PREFIX = f"PYSAI_1400_{uuid.uuid4().hex.upper()}"


@pytest.fixture
def conversation_factory():
    created = []

    def _create(**kwargs):
        attributes = ConversationAttributes(**kwargs)
        conv = Conversation(attributes=attributes)
        conv.create()
        created.append(conv)
        return conv

    yield _create

    for conv in created:
        conv.delete(force=True)


@pytest.fixture
def conversation(conversation_factory):
    return conversation_factory(title=f"{CONVERSATION_PREFIX}_ACTIVE")


def test_1400_create_with_title(conversation):
    """Create a conversation with title"""
    assert conversation.conversation_id


def test_1401_create_with_description(conversation_factory):
    """Create a conversation with title and description"""
    conv = conversation_factory(
        title=f"{CONVERSATION_PREFIX}_HISTORY",
        description="LLM's understanding of history of science",
    )
    attrs = conv.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_HISTORY"
    assert attrs.description == "LLM's understanding of history of science"


def test_1402_create_without_title(conversation_factory):
    """Create a conversation without providing a title"""
    conv = conversation_factory()
    attrs = conv.get_attributes()
    assert attrs.title == "New Conversation"


def test_1403_create_with_missing_attributes():
    """Missing attributes raise AttributeError"""
    conv = Conversation(attributes=None)
    with pytest.raises(AttributeError):
        conv.create()


def test_1404_get_attributes(conversation):
    """Fetch conversation attributes"""
    attrs = conversation.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_ACTIVE"
    assert attrs.description is None


def test_1405_set_attributes(conversation):
    """Update conversation attributes"""
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
    with pytest.raises(AttributeError):
        conversation.set_attributes(None)


def test_1407_delete_conversation(conversation_factory):
    """Delete conversation and validate removal"""
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_DELETE")
    conv.delete(force=True)
    with pytest.raises(select_ai.errors.ConversationNotFoundError):
        conv.get_attributes()


def test_1408_delete_twice(conversation_factory):
    """Deleting an already deleted conversation raises DatabaseError"""
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_DELETE_TWICE")
    conv.delete(force=True)
    with pytest.raises(DatabaseError):
        conv.delete()


def test_1409_list_contains_created_conversation(conversation):
    """Conversation list contains the created conversation"""
    conversation_ids = {item.conversation_id for item in Conversation.list()}
    assert conversation.conversation_id in conversation_ids


def test_1410_multiple_conversations_have_unique_ids(conversation_factory):
    """Multiple conversations produce unique identifiers"""
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
    conv = Conversation(
        attributes=ConversationAttributes(
            title="A" * 255,
            description="B" * 1000,
        )
    )
    with pytest.raises(Exception):
        conv.create()


def test_1412_set_attributes_with_invalid_id():
    """Updating conversation with invalid id raises DatabaseError"""
    conv = Conversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError):
        conv.set_attributes(ConversationAttributes(title="Invalid"))


def test_1413_delete_with_invalid_id():
    """Deleting conversation with invalid id raises DatabaseError"""
    conv = Conversation(conversation_id="fake_id")
    with pytest.raises(DatabaseError):
        conv.delete()


def test_1414_get_attributes_with_invalid_id():
    """Fetching attributes for invalid conversation raises ConversationNotFound"""
    conv = Conversation(conversation_id="invalid")
    with pytest.raises(select_ai.errors.ConversationNotFoundError):
        conv.get_attributes()


def test_1415_get_attributes_for_deleted_conversation(conversation_factory):
    """Fetching attributes after deletion raises ConversationNotFound"""
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_TO_DELETE")
    conv.delete(force=True)
    with pytest.raises(select_ai.errors.ConversationNotFoundError):
        conv.get_attributes()


def test_1416_list_contains_new_conversation(conversation_factory):
    """List reflects newly created conversation"""
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_LIST")
    listed = list(Conversation.list())
    assert any(item.conversation_id == conv.conversation_id for item in listed)


def test_1417_list_returns_conversation_instances():
    """List returns Conversation objects"""
    listed = list(Conversation.list())
    assert all(isinstance(item, Conversation) for item in listed)


def test_1418_get_attributes_without_description(conversation_factory):
    """Conversation created without description has None description"""
    conv = conversation_factory(title=f"{CONVERSATION_PREFIX}_NO_DESC")
    attrs = conv.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_NO_DESC"
    assert attrs.description is None


def test_1419_create_with_description_none(conversation_factory):
    """Explicitly setting description to None is allowed"""
    conv = conversation_factory(
        title=f"{CONVERSATION_PREFIX}_NONE_DESC",
        description=None,
    )
    attrs = conv.get_attributes()
    assert attrs.title == f"{CONVERSATION_PREFIX}_NONE_DESC"
    assert attrs.description is None
