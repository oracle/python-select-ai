# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1900 - Async chat session API tests
"""

import logging
import uuid

import pytest
import select_ai
from select_ai import (
    AsyncConversation,
    AsyncProfile,
    ConversationAttributes,
    ProfileAttributes,
)

logger = logging.getLogger(__name__)

PROFILE_PREFIX = f"PYSAI_1900_{uuid.uuid4().hex.upper()}"

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
def async_chat_session_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
async def async_chat_session_profile(
    oci_credential, async_chat_session_provider
):
    logger.info(
        "Creating async chat session profile %s", f"{PROFILE_PREFIX}_PROFILE"
    )
    profile = await AsyncProfile(
        profile_name=f"{PROFILE_PREFIX}_PROFILE",
        attributes=ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=[
                {"owner": "ADMIN", "name": "people"},
                {"owner": "ADMIN", "name": "gymnast"},
            ],
            provider=async_chat_session_provider,
        ),
        description="Async chat session test profile",
        replace=True,
    )
    await profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    logger.info("Deleting async chat session profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture
async def async_conversation_factory():
    conversations = []

    async def _create(**kwargs):
        logger.info("Creating async conversation with params %s", kwargs)
        conversation = AsyncConversation(
            attributes=ConversationAttributes(**kwargs)
        )
        await conversation.create()
        conversations.append(conversation)
        return conversation

    yield _create

    for conversation in conversations:
        logger.info(
            "Deleting async conversation %s", conversation.conversation_id
        )
        await conversation.delete(force=True)


async def _assert_keywords(session, prompts):
    for prompt, keyword in prompts:
        response = await session.chat(prompt=prompt)
        logger.debug("Async response for prompt '%s': %s", prompt, response)
        assert keyword.lower() in response.lower()


@pytest.mark.anyio
async def test_1900_database_chat_session(
    async_chat_session_profile, async_conversation_factory
):
    """Async chat session processes database prompts"""
    logger.info("Starting async database chat session test")
    conversation = await async_conversation_factory(
        title="Database",
        description="LLM's understanding of databases",
    )
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session:
        logger.info(
            "Async chat session started with conversation %s",
            conversation.conversation_id,
        )
        assert session is not None
        await _assert_keywords(session, CATEGORY_PROMPTS["database"])


@pytest.mark.anyio
async def test_1901_physics_chat_session_delete_true(
    async_chat_session_profile, async_conversation_factory
):
    """Async chat session deletes conversation when delete=True"""
    logger.info("Starting async physics chat session with delete=True")
    conversation = await async_conversation_factory(title="Physics")
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=True
    ) as session:
        logger.info(
            "Async chat session started for conversation %s with delete=True",
            conversation.conversation_id,
        )
        await _assert_keywords(session, CATEGORY_PROMPTS["physics"])
    with pytest.raises(Exception):
        await conversation.delete()


@pytest.mark.anyio
async def test_1902_multiple_sessions_same_conversation(
    async_chat_session_profile, async_conversation_factory
):
    """Same async conversation supports multiple chat sessions"""
    logger.info("Validating multiple async sessions for same conversation")
    conversation = await async_conversation_factory(
        title="Cloud Two Session",
        description="LLM's understanding of cloud using multiple chat sessions.",
    )
    async with async_chat_session_profile.chat_session(
        conversation=conversation
    ) as session_one:
        logger.info(
            "Async session one started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_one, CATEGORY_PROMPTS["cloud"][:3])
    async with async_chat_session_profile.chat_session(
        conversation=conversation
    ) as session_two:
        logger.info(
            "Async session two started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_two, CATEGORY_PROMPTS["cloud"][3:])


@pytest.mark.anyio
async def test_1903_many_sessions_same_conversation(
    async_chat_session_profile, async_conversation_factory
):
    """Conversation reused across several async sessions"""
    logger.info("Validating many async sessions for same conversation")
    conversation = await async_conversation_factory(
        title="Multi Session",
        description="LLM's understanding of cloud using multiple chat sessions.",
    )
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_one:
        logger.info(
            "Async session one started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_one, CATEGORY_PROMPTS["cloud"][:3])
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_two:
        logger.info(
            "Async session two started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_two, CATEGORY_PROMPTS["cloud"][3:])
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_three:
        logger.info(
            "Async session three started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_three, CATEGORY_PROMPTS["ai"][:3])
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_four:
        logger.info(
            "Async session four started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_four, CATEGORY_PROMPTS["ai"][3:])
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=False
    ) as session_five:
        logger.info(
            "Async session five started for conversation %s",
            conversation.conversation_id,
        )
        await _assert_keywords(session_five, CATEGORY_PROMPTS["general"])


@pytest.mark.anyio
async def test_1904_special_characters(
    async_chat_session_profile, async_conversation_factory
):
    """Async chat session handles special characters"""
    logger.info("Validating async special character handling in chat session")
    conversation = await async_conversation_factory(
        title="Special Character Test ✨😊你",
        description="♥️✨你好",
    )
    async with async_chat_session_profile.chat_session(
        conversation=conversation, delete=True
    ) as session:
        logger.info(
            "Async chat session started for special character conversation %s",
            conversation.conversation_id,
        )
        response = await session.chat(
            prompt="Tell me something with lot of emojis and special characters 🚀🔥"
        )
        assert isinstance(response, str)
        assert "error" not in response.lower()


@pytest.mark.anyio
async def test_1905_invalid_conversation_object(async_chat_session_profile):
    """Passing non conversation object raises error"""
    with pytest.raises(Exception):
        async with async_chat_session_profile.chat_session(
            conversation="fake-object"
        ):
            pass


@pytest.mark.anyio
async def test_1906_missing_conversation_attributes(
    async_chat_session_profile,
):
    """Conversation without attributes raises error"""
    conversation = AsyncConversation(attributes=None)
    with pytest.raises(Exception):
        async with async_chat_session_profile.chat_session(
            conversation=conversation
        ):
            await conversation.chat(prompt="Hello World")
