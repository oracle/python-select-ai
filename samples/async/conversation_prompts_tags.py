# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# async/conversation_prompts_tags.py
#
# Async version of the conversation prompt and tag sample. Requires
# SELECT_AI_PROFILE_NAME to name an existing AI profile.
# -----------------------------------------------------------------------------

import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")
profile_name = os.getenv("SELECT_AI_PROFILE_NAME", "oci_ai_profile")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    conversation = select_ai.AsyncConversation(
        attributes=select_ai.ConversationAttributes(
            title="Async prompt and tag sample"
        )
    )
    await conversation.create()
    profile = await select_ai.AsyncProfile(profile_name=profile_name)

    try:
        await conversation.add_tag("PROJECT", "SELECT_AI")
        await conversation.add_tag("PROJECT", "SELECT_AI_SAMPLES")
        async with profile.chat_session(conversation=conversation) as session:
            print(
                await session.chat(
                    "Reply with exactly: conversation history works."
                )
            )
        prompts = [prompt async for prompt in conversation.list_prompts()]
        for prompt in prompts:
            print(f"Prompt {prompt.conversation_prompt_id}: {prompt.prompt}")

        await conversation.delete_prompt(prompts[-1].conversation_prompt_id)
        prompts = [prompt async for prompt in conversation.list_prompts()]
        print("Prompts after deletion:", prompts)
        await conversation.remove_tag("PROJECT")
    finally:
        await conversation.delete(force=True)


asyncio.run(main())
