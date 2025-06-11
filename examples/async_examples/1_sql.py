import asyncio
import os

import select_ai

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


# This example shows how to asynchronously generate SQLs nad run SQLs
async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)

    provider = select_ai.OCIGenAIProvider(
        region="us-chicago-1", oci_apiformat="GENERIC"
    )

    profile_attributes = select_ai.ProfileAttributes(
        credential_name="my_oci_ai_profile_key",
        object_list=[{"owner": "SH"}],
        provider=provider,
    )

    async_profile = await select_ai.AsyncProfile(
        profile_name="async_oci_ai_profile",
        attributes=profile_attributes,
        description="MY OCI AI Profile",
        replace=True,
    )

    sql_tasks = [
        async_profile.show_sql(prompt="How many customers?"),
        async_profile.run_sql(prompt="How many promotions"),
        async_profile.explain_sql(prompt="How many promotions"),
    ]
    # Collect results from multiple asynchronous tasks
    for sql_task in asyncio.as_completed(sql_tasks):
        result = await sql_task
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
