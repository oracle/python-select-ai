import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


def main():
    select_ai.connect(user=user, password=password, dsn=dsn)
    if select_ai.is_connected():
        print("Connected to Database")
    else:
        raise Exception("Not connected to Database")
    profile = select_ai.Profile(
        profile_name="oci_ai_profile",
        fetch_and_merge_attributes=True,
    )
    conversation_attributes = select_ai.ConversationAttributes(
        title="History of Science",
        description="LLM's understanding of history of science",
    )
    conversation_id = profile.create_conversation(conversation_attributes)
    session_params = {"conversation_id": conversation_id}
    with select_ai.Session(profile=profile, params=session_params) as session:
        response = session.chat(
            prompt="What is importance of history of science ?"
        )
        print(response)
        response = session.chat(
            prompt="Elaborate more on 'Learning from past mistakes'"
        )
        print(response)


if __name__ == "__main__":
    main()
