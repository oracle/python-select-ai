import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    oci_provider_attributes = select_ai.OCIGenAIProviderAttributes(
        model="meta.llama-3.1-70b-instruct"
    )
    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
        attributes=oci_provider_attributes,
        description="MY OCI AI Profile",
        fetch_and_merge_attributes=True,
    )

    # Asynchronously send multiple prompts
    chat_tasks = [
        async_profile.chat(prompt="What is OCI ?"),
        async_profile.chat(prompt="What is OML4PY?"),
        async_profile.chat(prompt="What is Autonomous Database ?"),
    ]
    for chat_task in asyncio.as_completed(chat_tasks):
        result = await chat_task
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
