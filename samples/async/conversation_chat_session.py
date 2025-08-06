# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# async/conversation_chat_session.py
#
# Demonstrates context aware conversation using AI Profile
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile"
    )
    conversation_attributes = select_ai.ConversationAttributes(
        title="History of Science",
        description="LLM's understanding of history of science",
    )
    async_conversation = select_ai.AsyncConversation(
        attributes=conversation_attributes
    )

    async with async_profile.chat_session(
        conversation=async_conversation, delete=True
    ) as async_session:
        response = await async_session.chat(
            prompt="What is importance of history of science ?"
        )
        print(response)
        response = await async_session.chat(
            prompt="Elaborate more on 'Learning from past mistakes'"
        )
        print(response)


asyncio.run(main())
