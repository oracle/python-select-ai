# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# agent/async/tool_run_describe.py
#
# Async version of the direct tool execution sample. The database user needs
# permission to create a function.
# -----------------------------------------------------------------------------

import asyncio
import os
import uuid

import select_ai
from select_ai.agent import AsyncTool

user = os.getenv("SELECT_AI_USER")
password = os.getenv("SELECT_AI_PASSWORD")
dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


async def main():
    await select_ai.async_connect(user=user, password=password, dsn=dsn)
    suffix = uuid.uuid4().hex.upper()
    function_name = f"SAMPLE_CALCULATE_AGE_{suffix}"
    tool_name = f"SAMPLE_AGE_TOOL_{suffix}"

    async with select_ai.async_cursor() as cursor:
        await cursor.execute(
            f"""
            CREATE OR REPLACE FUNCTION {function_name}(p_birth_date DATE)
            RETURN NUMBER IS
            BEGIN
                RETURN TRUNC(MONTHS_BETWEEN(SYSDATE, p_birth_date) / 12);
            END;
            """
        )

    tool = await AsyncTool.create_pl_sql_tool(
        tool_name=tool_name,
        function=function_name,
        description="Calculate age from a birth date",
    )

    try:
        print("Tool description:")
        print(await tool.describe_tool())
        print("Tool result:")
        print(await tool.run_tool('{"p_birth_date":"2000-01-01"}'))
    finally:
        await tool.delete(force=True)
        async with select_ai.async_cursor() as cursor:
            await cursor.execute(f"DROP FUNCTION {function_name}")


asyncio.run(main())
