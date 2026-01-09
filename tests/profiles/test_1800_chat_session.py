# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1800 - Chat session API tests
"""

import logging
import uuid

import pytest
import select_ai
from select_ai import (
    Conversation,
    ConversationAttributes,
    Profile,
    ProfileAttributes,
)

logger = logging.getLogger(__name__)

PROFILE_PREFIX = f"PYSAI_1800_{uuid.uuid4().hex.upper()}"

CATEGORY_PROMPTS = {
    "database": [
        ("What is a database?", "database"),
        ("Explain the difference between SQL and NoSQL.", "sql"),
        ("Give me an example of a SQL SELECT query.", "select"),
        ("How do transactions ensure consistency?", "transaction"),
        ("What are indexes and why are they used?", "index"),
    ],
    "cloud": [
        ("What is cloud computing?", "cloud"),
        ("Explain IaaS, PaaS, and SaaS briefly.", "iaas"),
        ("What is the benefit of auto-scaling?", "scaling"),
        ("How do cloud regions and availability zones differ?", "region"),
        ("What is serverless computing?", "serverless"),
    ],
    "ai": [
        ("What is artificial intelligence?", "intelligence"),
        ("Explain supervised vs unsupervised learning.", "supervised"),
        ("What are neural networks?", "neural"),
        ("How does reinforcement learning work?", "reinforcement"),
        ("Give me a real-world use case of AI.", "ai"),
    ],
    "physics": [
        ("What is Newton's first law?", "newton"),
        ("Explain the concept of gravity.", "gravity"),
        ("How does friction affect motion?", "friction"),
        ("What is the difference between speed and velocity?", "velocity"),
        ("Explain kinetic and potential energy with examples.", "energy"),
    ],
    "general": [
        ("What is the capital of Japan?", "tokyo"),
        ("Tell me a fun fact about space.", "space"),
        ("Who invented the telephone?", "telephone"),
        ("What is the fastest land animal?", "cheetah"),
        ("Explain why the sky looks blue.", "sky"),
    ],
}


@pytest.fixture(scope="module")
def chat_session_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
def chat_session_profile(oci_credential, chat_session_provider):
    logger.info(
        "Creating chat session profile %s", f"{PROFILE_PREFIX}_PROFILE"
    )
    profile = Profile(
        profile_name=f"{PROFILE_PREFIX}_PROFILE",
        attributes=ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=[
                {"owner": "ADMIN", "name": "people"},
                {"owner": "ADMIN", "name": "gymnast"},
            ],
            provider=chat_session_provider,
        ),
        description="Chat session test profile",
        replace=True,
    )
    profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    logger.info("Deleting chat session profile %s", profile.profile_name)
    profile.delete(force=True)


@pytest.fixture
def conversation_factory():
    conversations = []

    def _create(**kwargs):
        logger.info("Creating conversation with params %s", kwargs)
        conversation = Conversation(
            attributes=ConversationAttributes(**kwargs)
        )
        conversation.create()
        conversations.append(conversation)
        return conversation

    yield _create

    for conversation in conversations:
        logger.info("Deleting conversation %s", conversation.conversation_id)
        conversation.delete(force=True)


def _assert_keywords(session, prompts):
    for prompt, keyword in prompts:
        response = session.chat(prompt=prompt)
        logger.debug("Received response for prompt '%s': %s", prompt, response)
        assert keyword.lower() in response.lower()


def test_1800_database_chat_session(
    chat_session_profile, conversation_factory
):
    """Chat session processes database prompts"""
    logger.info("Starting database chat session test")
    conversation = conversation_factory(
        title="Database",
        description="LLM's understanding of databases",
    )
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session:
        logger.info(
            "Chat session started with conversation %s",
            conversation.conversation_id,
        )
        assert session is not None
        _assert_keywords(session, CATEGORY_PROMPTS["database"])


def test_1801_physics_chat_session_delete_true(
    chat_session_profile, conversation_factory
):
    """Chat session deletes conversation when delete=True"""
    logger.info("Starting physics chat session with delete=True")
    conversation = conversation_factory(title="Physics")
    with chat_session_profile.chat_session(
        conversation=conversation, delete=True
    ) as session:
        logger.info(
            "Chat session started for conversation %s with delete=True",
            conversation.conversation_id,
        )
        _assert_keywords(session, CATEGORY_PROMPTS["physics"])
    with pytest.raises(Exception):
        conversation.delete()


def test_1802_multiple_sessions_same_conversation(
    chat_session_profile, conversation_factory
):
    """Same conversation supports multiple chat sessions"""
    logger.info("Validating multiple sessions for same conversation")
    conversation = conversation_factory(
        title="Cloud Two Session",
        description="LLM's understanding of cloud using multiple chat sessions.",
    )
    with chat_session_profile.chat_session(
        conversation=conversation
    ) as session_one:
        logger.info(
            "First session started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_one, CATEGORY_PROMPTS["cloud"][:3])
    with chat_session_profile.chat_session(
        conversation=conversation
    ) as session_two:
        logger.info(
            "Second session started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_two, CATEGORY_PROMPTS["cloud"][3:])


def test_1803_many_sessions_same_conversation(
    chat_session_profile, conversation_factory
):
    """Conversation reused across several sessions"""
    logger.info("Validating many sessions for same conversation")
    conversation = conversation_factory(
        title="Multi Session",
        description="LLM's understanding of cloud using multiple chat sessions.",
    )
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_one:
        logger.info(
            "Session one started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_one, CATEGORY_PROMPTS["cloud"][:3])
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_two:
        logger.info(
            "Session two started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_two, CATEGORY_PROMPTS["cloud"][3:])
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_three:
        logger.info(
            "Session three started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_three, CATEGORY_PROMPTS["ai"][:3])
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_four:
        logger.info(
            "Session four started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_four, CATEGORY_PROMPTS["ai"][3:])
    with chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_five:
        logger.info(
            "Session five started for conversation %s",
            conversation.conversation_id,
        )
        _assert_keywords(session_five, CATEGORY_PROMPTS["general"])


def test_1804_special_characters(chat_session_profile, conversation_factory):
    """Chat session handles special characters"""
    logger.info("Validating special character handling in chat session")
    conversation = conversation_factory(
        title="Special Character Test ✨😊你",
        description="♥️✨你好",
    )
    with chat_session_profile.chat_session(
        conversation=conversation, delete=True
    ) as session:
        logger.info(
            "Chat session started for special character conversation %s",
            conversation.conversation_id,
        )
        response = session.chat(
            prompt="Tell me something with lot of emojis and special characters 🚀🔥"
        )
        assert isinstance(response, str)
        assert "error" not in response.lower()


def test_1805_invalid_conversation_object(chat_session_profile):
    """Passing non conversation object raises error"""
    logger.info("Validating invalid conversation object handling")
    with pytest.raises(Exception):
        with chat_session_profile.chat_session(conversation="fake-object"):
            pass


# def test_1806_missing_conversation_attributes(chat_session_profile):
#     """Conversation without attributes raises error"""
#     conversation = Conversation(attributes=None)
#     with pytest.raises(Exception):
#         with chat_session_profile.chat_session(conversation=conversation):
#             _assert_keywords(chat_session_profile, [("Hello World", "hello")])
