import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    async for conversation in select_ai.AsyncConversation().list():
        print(conversation.conversation_id)
        print(conversation.attributes)


if __name__ == "__main__":
    asyncio.run(main())
