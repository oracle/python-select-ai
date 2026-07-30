# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# conversation_prompts_tags.py
#
# Create conversation history, add and remove tags, and delete a stored prompt.
# Requires SELECT_AI_PROFILE_NAME to name an existing AI profile.
# -----------------------------------------------------------------------------

import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

select_ai.connect(user=user, password=password, dsn=dsn)

conversation = select_ai.Conversation(
    attributes=select_ai.ConversationAttributes(title="Prompt and tag sample")
)
conversation.create()
profile = select_ai.Profile(profile_name="oci_ai_profile")

try:
    conversation.add_tag("PROJECT", "SELECT_AI")
    conversation.add_tag("PROJECT", "SELECT_AI_SAMPLES")  # Updates the tag.
    with profile.chat_session(conversation=conversation) as session:
        print(session.chat("Reply with exactly: conversation history works."))

    prompts = list(conversation.list_prompts())
    for prompt in prompts:
        print(f"Prompt {prompt.conversation_prompt_id}: {prompt.prompt}")

    conversation.delete_prompt(prompts[-1].conversation_prompt_id)
    print("Prompts after deletion:", list(conversation.list_prompts()))
    conversation.remove_tag("PROJECT")
finally:
    conversation.delete(force=True)
