import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    if await select_ai.async_is_connected():
        print("Connected to Database")
    else:
        raise Exception("Not connected to Database")

    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
        fetch_and_merge_attributes=True,
    )

    prompt_specifications = [
        ("What is Oracle Autonomous Database?", select_ai.Action.CHAT),
        ("Generate SQL to list all customers?", select_ai.Action.SHOWSQL),
        (
            "Explain the query: SELECT * FROM sh.products",
            select_ai.Action.EXPLAINSQL,
        ),
        ("Explain the query: SELECT * FROM sh.products", "INVALID ACTION"),
    ]

    # 1. Multiple prompts are sent in a single roundtrip to the Database
    # 2. Results are returned as soon as Database has executed all prompts
    # 3. Application doesn't have to wait on one response before sending
    #    the next prompts
    # 4. Fewer round trips and database is kept busy
    # 5. Efficient network usage
    results = await async_profile.run_pipeline(
        prompt_specifications, continue_on_error=True
    )

    for i, result in enumerate(results):
        print(
            f"Result {i} for prompt '{prompt_specifications[i][0]}' is: {result}"
        )


if __name__ == "__main__":
    asyncio.run(main())
