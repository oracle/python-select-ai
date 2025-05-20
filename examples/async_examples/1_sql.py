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

    oci_provider_attributes = select_ai.OCIGenAIProviderAttributes(
        region="us-chicago-1",
        credential_name="my_oci_ai_profile_key",
        oci_apiformat="GENERIC",
        object_list=[{"owner": "SH"}],
    )

    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
        attributes=oci_provider_attributes,
        description="MY OCI AI Profile",
        replace=True,
    )

    sql_tasks = [
        async_profile.show_sql(prompt="How many customers?"),
        async_profile.run_sql(prompt="How many promotions"),
    ]
    # Collect results from multiple asynchronous tasks
    for sql_task in asyncio.as_completed(sql_tasks):
        result = await sql_task
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
