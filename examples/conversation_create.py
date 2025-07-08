import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


# This example shows how to create a conversation
def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    conversation_attributes = select_ai.ConversationAttributes(
        title="History of Science",
        description="LLM's understanding of history of science",
    )

    conversation = select_ai.Conversation(attributes=conversation_attributes)
    conversation.create()

    print(
        "Created conversation with conversation id: ",
        conversation.conversation_id,
    )


if __name__ == "__main__":
    main()
