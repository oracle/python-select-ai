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
    # matches the start of string
    async for fetched_profile in async_profile.list(
        profile_name_pattern="^oci"
    ):
        p = await fetched_profile
        print(p)


if __name__ == "__main__":
    asyncio.run(main())
