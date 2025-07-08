import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


# This example shows how to create a conversation
def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    conversation = select_ai.Conversation(
        conversation_id="37DDC22E-11C8-3D49-E063-D81A000A85FE"
    )
    conversation.delete(force=True)
    print(
        "Deleted conversation with conversation id: ",
        conversation.conversation_id,
    )


if __name__ == "__main__":
    main()
