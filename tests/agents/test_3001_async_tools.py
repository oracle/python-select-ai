# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3001 - Async API coverage for select_ai.agent AsyncTool APIs
"""

import logging
import os
import uuid

import oracledb
import pytest
import select_ai
from select_ai.agent import AsyncTool
from select_ai.errors import AgentToolNotFoundError

pytestmark = pytest.mark.anyio

# Path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3001_async_tools.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Force logging to file (pytest-proof)
root = logging.getLogger()
root.setLevel(logging.INFO)
for handler in root.handlers[:]:
    root.removeHandler(handler)
file_handler = logging.FileHandler(LOG_FILE, mode="w")
file_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(file_handler)
logger = logging.getLogger()

UUID = uuid.uuid4().hex.upper()

SQL_PROFILE_NAME = f"PYSAI_3001_SQL_PROFILE_{UUID}"
RAG_PROFILE_NAME = f"PYSAI_3001_RAG_PROFILE_{UUID}"

SQL_TOOL_NAME = f"PYSAI_3001_SQL_TOOL_{UUID}"
RAG_TOOL_NAME = f"PYSAI_3001_RAG_TOOL_{UUID}"
PLSQL_TOOL_NAME = f"PYSAI_3001_PLSQL_TOOL_{UUID}"
WEB_SEARCH_TOOL_NAME = f"PYSAI_3001_WEB_TOOL_{UUID}"
PLSQL_FUNCTION_NAME = f"PYSAI_3001_CALC_AGE_{UUID}"
CUSTOM_ATTR_TOOL_NAME = f"PYSAI_3001_CUSTOM_ATTR_TOOL_{UUID}"
CUSTOM_ATTR_TOOL_DESCRIPTION = "Custom attr tool for async testing"
CUSTOM_NO_TYPE_TOOL_NAME = f"PYSAI_3001_CUSTOM_NO_TYPE_TOOL_{UUID}"
CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME = (
    f"PYSAI_3001_CUSTOM_WITH_TYPE_NO_INSTR_TOOL_{UUID}"
)
CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME = (
    f"PYSAI_3001_CUSTOM_WITH_TYPE_AND_INSTR_TOOL_{UUID}"
)
DISABLED_TOOL_NAME = f"PYSAI_3001_DISABLED_TOOL_{UUID}"
DEFAULT_STATUS_TOOL_NAME = f"PYSAI_3001_DEFAULT_STATUS_TOOL_{UUID}"
DROP_FORCE_MISSING_TOOL = f"PYSAI_3001_DROP_MISSING_{UUID}"
HTTP_TOOL_NAME = f"PYSAI_3001_HTTP_TOOL_{UUID}"
HTTP_ENDPOINT = "https://example.com/api/tool"

EMAIL_TOOL_NAME = f"PYSAI_3001_EMAIL_TOOL_{UUID}"
SLACK_TOOL_NAME = f"PYSAI_3001_SLACK_TOOL_{UUID}"

NEG_SQL_TOOL_NAME = f"PYSAI_3001_NEG_SQL_TOOL_{UUID}"
NEG_RAG_TOOL_NAME = f"PYSAI_3001_NEG_RAG_TOOL_{UUID}"
NEG_PLSQL_TOOL_NAME = f"PYSAI_3001_NEG_PLSQL_TOOL_{UUID}"

EMAIL_CRED_NAME = f"PYSAI_3001_EMAIL_CRED_{UUID}"
SLACK_CRED_NAME = f"PYSAI_3001_SLACK_CRED_{UUID}"

EMAIL_RECIPIENT = os.getenv("PYSAI_TEST_EMAIL_RECIPIENT")
EMAIL_SENDER = os.getenv("PYSAI_TEST_EMAIL_SENDER")
EMAIL_SMTP_HOST = os.getenv("PYSAI_TEST_EMAIL_SMTPHOST")
SMTP_USERNAME = os.getenv("PYSAI_TEST_EMAIL_CRED_USERNAME")
SMTP_PASSWORD = os.getenv("PYSAI_TEST_EMAIL_CRED_PASSWORD")
SLACK_USERNAME = os.getenv("PYSAI_TEST_SLACK_USERNAME")
SLACK_PASSWORD = os.getenv("PYSAI_TEST_SLACK_PASSWORD")


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


async def get_tool_status(tool_name):
    logger.info("Fetching tool status for: %s", tool_name)
    async with select_ai.async_cursor() as cur:
        await cur.execute(
            """
            SELECT status
            FROM USER_AI_AGENT_TOOLS
            WHERE tool_name = :tool_name
            """,
            {"tool_name": tool_name},
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def assert_tool_status(tool_name: str, expected_status: str) -> None:
    status = await get_tool_status(tool_name)
    logger.info(
        "Verifying tool status | tool=%s | expected=%s | actual=%s",
        tool_name,
        expected_status,
        status,
    )
    assert status == expected_status


def log_tool_details(context: str, tool) -> None:
    attrs = getattr(tool, "attributes", None)
    tool_params = getattr(attrs, "tool_params", None) if attrs else None

    details = {
        "context": context,
        "tool_name": getattr(tool, "tool_name", None),
        "description": getattr(tool, "description", None),
        "tool_type": str(getattr(attrs, "tool_type", None)) if attrs else None,
        "instruction": getattr(attrs, "instruction", None) if attrs else None,
        "function": getattr(attrs, "function", None) if attrs else None,
        "tool_inputs": getattr(attrs, "tool_inputs", None) if attrs else None,
        "tool_params": (
            tool_params.dict(exclude_null=False)
            if tool_params is not None
            else None
        ),
    }

    logger.info("TOOL_DETAILS: %s", details)
    print("TOOL_DETAILS:", details)


@pytest.fixture(scope="module")
async def sql_profile(profile_attributes):
    logger.info("Creating SQL profile: %s", SQL_PROFILE_NAME)
    profile = await select_ai.AsyncProfile(
        profile_name=SQL_PROFILE_NAME,
        description="SQL Profile",
        attributes=profile_attributes,
    )
    yield profile
    logger.info("Deleting SQL profile: %s", SQL_PROFILE_NAME)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def rag_profile(rag_profile_attributes):
    logger.info("Creating RAG profile: %s", RAG_PROFILE_NAME)
    profile = await select_ai.AsyncProfile(
        profile_name=RAG_PROFILE_NAME,
        description="RAG Profile",
        attributes=rag_profile_attributes,
    )
    yield profile
    logger.info("Deleting RAG profile: %s", RAG_PROFILE_NAME)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def sql_tool(sql_profile):
    logger.info("Creating SQL tool: %s", SQL_TOOL_NAME)
    tool = await AsyncTool.create_sql_tool(
        tool_name=SQL_TOOL_NAME,
        profile_name=SQL_PROFILE_NAME,
        description="SQL Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting SQL tool: %s", SQL_TOOL_NAME)
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def rag_tool(rag_profile):
    logger.info("Creating RAG tool: %s", RAG_TOOL_NAME)
    tool = await AsyncTool.create_rag_tool(
        tool_name=RAG_TOOL_NAME,
        profile_name=RAG_PROFILE_NAME,
        description="RAG Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting RAG tool: %s", RAG_TOOL_NAME)
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def plsql_function():
    logger.info("Creating PL/SQL function: %s", PLSQL_FUNCTION_NAME)
    ddl = f"""
    CREATE OR REPLACE FUNCTION {PLSQL_FUNCTION_NAME}(p_birth_date DATE)
    RETURN NUMBER IS
    BEGIN
        RETURN TRUNC(MONTHS_BETWEEN(SYSDATE, p_birth_date) / 12);
    END;
    """

    async with select_ai.async_cursor() as cur:
        await cur.execute(ddl)

    yield

    logger.info("Dropping PL/SQL function: %s", PLSQL_FUNCTION_NAME)
    async with select_ai.async_cursor() as cur:
        await cur.execute(f"DROP FUNCTION {PLSQL_FUNCTION_NAME}")


@pytest.fixture(scope="module")
async def plsql_tool(plsql_function):
    logger.info("Creating PL/SQL tool: %s", PLSQL_TOOL_NAME)
    tool = await AsyncTool.create_pl_sql_tool(
        tool_name=PLSQL_TOOL_NAME,
        function=PLSQL_FUNCTION_NAME,
        description="PL/SQL Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting PL/SQL tool: %s", PLSQL_TOOL_NAME)
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def web_search_tool():
    logger.info("Creating Web Search tool: %s", WEB_SEARCH_TOOL_NAME)
    tool = await AsyncTool.create_websearch_tool(
        tool_name=WEB_SEARCH_TOOL_NAME,
        description="Web Search Tool for testing",
        credential_name="OPENAI_CRED",
        replace=True,
    )
    yield tool
    logger.info("Deleting Web Search tool: %s", WEB_SEARCH_TOOL_NAME)
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def email_credential():
    logger.info("Ensuring EMAIL credential is clean: %s", EMAIL_CRED_NAME)
    credential = {
        "credential_name": EMAIL_CRED_NAME,
        "username": SMTP_USERNAME,
        "password": SMTP_PASSWORD,
    }

    try:
        await select_ai.async_delete_credential(EMAIL_CRED_NAME, force=True)
    except Exception:
        logger.info("EMAIL credential did not exist or could not be dropped")
        pass

    await select_ai.async_create_credential(
        credential=credential, replace=True
    )
    logger.info("Created EMAIL credential: %s", EMAIL_CRED_NAME)
    yield EMAIL_CRED_NAME

    logger.info("Deleting EMAIL credential: %s", EMAIL_CRED_NAME)
    try:
        await select_ai.async_delete_credential(EMAIL_CRED_NAME, force=True)
    except Exception:
        logger.warning("Failed to delete EMAIL credential during teardown")
        pass


@pytest.fixture(scope="module")
async def slack_credential():
    logger.info("Ensuring SLACK credential is clean: %s", SLACK_CRED_NAME)
    credential = {
        "credential_name": SLACK_CRED_NAME,
        "username": SLACK_USERNAME,
        "password": SLACK_PASSWORD,
    }

    try:
        await select_ai.async_delete_credential(SLACK_CRED_NAME, force=True)
    except Exception:
        logger.info("SLACK credential did not exist or could not be dropped")
        pass

    await select_ai.async_create_credential(
        credential=credential, replace=True
    )
    logger.info("Created SLACK credential: %s", SLACK_CRED_NAME)
    yield SLACK_CRED_NAME

    logger.info("Deleting SLACK credential: %s", SLACK_CRED_NAME)
    try:
        await select_ai.async_delete_credential(SLACK_CRED_NAME, force=True)
    except Exception:
        logger.warning("Failed to delete SLACK credential during teardown")
        pass


@pytest.fixture(scope="module")
async def email_tool(email_credential):
    logger.info("Creating EMAIL tool: %s", EMAIL_TOOL_NAME)
    tool = await AsyncTool.create_email_notification_tool(
        tool_name=EMAIL_TOOL_NAME,
        credential_name=EMAIL_CRED_NAME,
        recipient=EMAIL_RECIPIENT,
        sender=EMAIL_SENDER,
        smtp_host=EMAIL_SMTP_HOST,
        description="Send email",
        replace=True,
    )
    yield tool
    logger.info("Deleting EMAIL tool: %s", EMAIL_TOOL_NAME)
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def slack_tool(slack_credential):
    logger.info("Creating SLACK tool: %s", SLACK_TOOL_NAME)
    tool = None
    try:
        tool = await AsyncTool.create_slack_notification_tool(
            tool_name=SLACK_TOOL_NAME,
            credential_name=SLACK_CRED_NAME,
            channel="#general",
            description="slack notification",
            replace=True,
        )
        logger.info("SLACK tool created successfully: %s", SLACK_TOOL_NAME)
        yield tool
    except oracledb.DatabaseError as e:
        if "ORA-20052" in str(e):
            logger.info("Expected ORA-20052 during SLACK tool creation: %s", e)
            yield None
        else:
            raise
    finally:
        if tool is not None:
            logger.info("Deleting SLACK tool: %s", SLACK_TOOL_NAME)
            await tool.delete(force=True)


@pytest.fixture(scope="module")
async def neg_sql_tool():
    logger.info(
        "Creating SQL tool with invalid profile: %s", NEG_SQL_TOOL_NAME
    )
    tool = await AsyncTool.create_sql_tool(
        tool_name=NEG_SQL_TOOL_NAME,
        profile_name="NON_EXISTENT_PROFILE",
        replace=True,
    )
    yield tool
    logger.info(
        "Deleting SQL tool with invalid profile: %s", NEG_SQL_TOOL_NAME
    )
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def neg_rag_tool():
    logger.info(
        "Creating RAG tool with invalid profile: %s", NEG_RAG_TOOL_NAME
    )
    tool = await AsyncTool.create_rag_tool(
        tool_name=NEG_RAG_TOOL_NAME,
        profile_name="NON_EXISTENT_RAG_PROFILE",
        replace=True,
    )
    yield tool
    logger.info(
        "Deleting RAG tool with invalid profile: %s", NEG_RAG_TOOL_NAME
    )
    await tool.delete(force=True)


@pytest.fixture(scope="module")
async def neg_plsql_tool():
    logger.info(
        "Creating PL/SQL tool with invalid function: %s", NEG_PLSQL_TOOL_NAME
    )
    tool = await AsyncTool.create_pl_sql_tool(
        tool_name=NEG_PLSQL_TOOL_NAME,
        function="NON_EXISTENT_FUNCTION",
        replace=True,
    )
    yield tool
    logger.info(
        "Deleting PL/SQL tool with invalid function: %s", NEG_PLSQL_TOOL_NAME
    )
    await tool.delete(force=True)


async def test_3000_sql_tool_created(sql_tool):
    logger.info("Validating SQL tool creation: %s", SQL_TOOL_NAME)
    log_tool_details("test_3000_sql_tool_created", sql_tool)
    assert sql_tool.tool_name == SQL_TOOL_NAME
    assert sql_tool.description == "SQL Tool"
    assert sql_tool.attributes.tool_type == select_ai.agent.ToolType.SQL
    assert sql_tool.attributes.tool_params is not None
    assert sql_tool.attributes.tool_params.profile_name == SQL_PROFILE_NAME


async def test_3001_rag_tool_created(rag_tool):
    logger.info("Validating RAG tool creation: %s", RAG_TOOL_NAME)
    log_tool_details("test_3001_rag_tool_created", rag_tool)
    assert rag_tool.tool_name == RAG_TOOL_NAME
    assert rag_tool.description == "RAG Tool"
    assert rag_tool.attributes.tool_type == select_ai.agent.ToolType.RAG
    assert rag_tool.attributes.tool_params is not None
    assert rag_tool.attributes.tool_params.profile_name == RAG_PROFILE_NAME


async def test_3002_plsql_tool_created(plsql_tool):
    logger.info("Validating PL/SQL tool creation: %s", PLSQL_TOOL_NAME)
    log_tool_details("test_3002_plsql_tool_created", plsql_tool)
    assert plsql_tool.tool_name == PLSQL_TOOL_NAME
    assert plsql_tool.description == "PL/SQL Tool"
    assert plsql_tool.attributes.tool_type is None
    assert plsql_tool.attributes.function == PLSQL_FUNCTION_NAME


async def test_3003_list_tools():
    logger.info("Listing all tools")
    tools = [tool async for tool in AsyncTool.list()]
    for tool in tools:
        if tool.tool_name in {SQL_TOOL_NAME, RAG_TOOL_NAME, PLSQL_TOOL_NAME}:
            log_tool_details("test_3003_list_tools", tool)
    tool_names = {tool.tool_name for tool in tools}
    logger.info("Tools present: %s", tool_names)
    assert len(tools) >= 3
    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


async def test_3004_list_tools_regex():
    logger.info("Listing tools with regex: ^PYSAI_3001_")
    tools = [
        tool async for tool in AsyncTool.list(tool_name_pattern="^PYSAI_3001_")
    ]
    for tool in tools:
        log_tool_details("test_3004_list_tools_regex", tool)
    tool_names = {tool.tool_name for tool in tools}
    logger.info("Matched tools: %s", tool_names)
    assert len(tools) >= 3
    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


async def test_3005_fetch_tool():
    logger.info("Fetching SQL tool: %s", SQL_TOOL_NAME)
    tool = await AsyncTool.fetch(SQL_TOOL_NAME)
    logger.info(
        "Fetched SQL tool | name=%s | type=%s | profile=%s",
        tool.tool_name,
        tool.attributes.tool_type,
        tool.attributes.tool_params.profile_name,
    )
    log_tool_details("test_3005_fetch_tool", tool)
    assert tool.tool_name == SQL_TOOL_NAME
    assert tool.attributes.tool_type == select_ai.agent.ToolType.SQL
    assert tool.attributes.tool_params.profile_name == SQL_PROFILE_NAME


async def test_3006_enable_disable_sql_tool(sql_tool):
    logger.info("Disabling SQL tool: %s", sql_tool.tool_name)
    await sql_tool.disable()
    await assert_tool_status(sql_tool.tool_name, "DISABLED")

    logger.info("Enabling SQL tool: %s", sql_tool.tool_name)
    await sql_tool.enable()
    await assert_tool_status(sql_tool.tool_name, "ENABLED")


async def test_3007_web_search_tool_created(web_search_tool):
    logger.info(
        "Validating Web Search tool creation: %s", WEB_SEARCH_TOOL_NAME
    )
    log_tool_details("test_3007_web_search_tool_created", web_search_tool)
    assert web_search_tool.tool_name == WEB_SEARCH_TOOL_NAME
    assert (
        web_search_tool.attributes.tool_type
        == select_ai.agent.ToolType.WEBSEARCH
    )
    assert (
        web_search_tool.attributes.tool_params.credential_name == "OPENAI_CRED"
    )


async def test_3008_email_tool_created(email_tool):
    logger.info("Validating EMAIL tool creation: %s", EMAIL_TOOL_NAME)
    log_tool_details("test_3008_email_tool_created", email_tool)
    assert email_tool.tool_name == EMAIL_TOOL_NAME
    assert str(email_tool.attributes.tool_type).upper() in (
        "EMAIL",
        "NOTIFICATION",
    )
    assert email_tool.attributes.tool_params.credential_name == EMAIL_CRED_NAME
    assert email_tool.attributes.tool_params.smtp_host is not None
    assert (
        str(email_tool.attributes.tool_params.notification_type).lower()
        == "email"
    )


async def test_3009_slack_tool_created(slack_tool):
    logger.info("Validating SLACK tool creation: %s", SLACK_TOOL_NAME)
    if slack_tool is not None:
        log_tool_details("test_3009_slack_tool_created", slack_tool)
        assert slack_tool.tool_name == SLACK_TOOL_NAME
        assert str(slack_tool.attributes.tool_type).upper() in (
            "SLACK",
            "NOTIFICATION",
        )
        assert (
            slack_tool.attributes.tool_params.credential_name
            == SLACK_CRED_NAME
        )
        assert (
            str(slack_tool.attributes.tool_params.notification_type).lower()
            == "slack"
        )
    else:
        logger.info(
            "SLACK tool not created due to expected backend-side error"
        )


async def test_3010_custom_tool_attributes_roundtrip():
    logger.info(
        "Validating custom tool attribute roundtrip: instruction/tool_inputs/description"
    )
    tool = AsyncTool(
        tool_name=CUSTOM_ATTR_TOOL_NAME,
        description=CUSTOM_ATTR_TOOL_DESCRIPTION,
        attributes=select_ai.agent.ToolAttributes(
            function=PLSQL_FUNCTION_NAME,
            instruction="Return age in years for a birth date input",
            tool_inputs=[
                {
                    "name": "p_birth_date",
                    "description": "Input birth date in DATE format",
                }
            ],
        ),
    )
    await tool.create(replace=True)
    try:
        fetched = await AsyncTool.fetch(CUSTOM_ATTR_TOOL_NAME)
        log_tool_details("test_3009_custom_tool_attributes_roundtrip", fetched)
        logger.info(
            "Fetched custom tool | name=%s | description=%s | instruction=%s",
            fetched.tool_name,
            fetched.description,
            fetched.attributes.instruction,
        )
        assert fetched.tool_name == CUSTOM_ATTR_TOOL_NAME
        assert fetched.description == CUSTOM_ATTR_TOOL_DESCRIPTION
        assert fetched.attributes.function == PLSQL_FUNCTION_NAME
        assert (
            fetched.attributes.instruction
            == "Return age in years for a birth date input"
        )
        assert isinstance(fetched.attributes.tool_inputs, list)
        assert fetched.attributes.tool_inputs[0]["name"] == "p_birth_date"
        assert (
            "birth date"
            in fetched.attributes.tool_inputs[0]["description"].lower()
        )
    finally:
        await tool.delete(force=True)


async def test_3011_custom_tool_without_tool_type():
    logger.info("Validating custom tool creation with tool_type unset")
    tool = AsyncTool(
        tool_name=CUSTOM_NO_TYPE_TOOL_NAME,
        description="Custom tool without tool_type",
        attributes=select_ai.agent.ToolAttributes(
            function=PLSQL_FUNCTION_NAME,
            instruction="Calculate age from birth date",
        ),
    )
    await tool.create(replace=True)
    try:
        fetched = await AsyncTool.fetch(CUSTOM_NO_TYPE_TOOL_NAME)
        logger.info(
            "Fetched custom tool | name=%s | type=%s | function=%s | instruction=%s",
            fetched.tool_name,
            fetched.attributes.tool_type,
            fetched.attributes.function,
            fetched.attributes.instruction,
        )
        log_tool_details("test_3009_custom_tool_without_tool_type", fetched)
        assert fetched.tool_name == CUSTOM_NO_TYPE_TOOL_NAME
        assert fetched.attributes.tool_type is None
        assert fetched.attributes.function == PLSQL_FUNCTION_NAME
        assert (
            fetched.attributes.instruction == "Calculate age from birth date"
        )
    finally:
        await tool.delete(force=True)


async def test_3012_custom_tool_with_tool_type_without_instruction(
    sql_profile,
):
    logger.info(
        "Validating custom tool creation with tool_type set and instruction unset"
    )
    tool = AsyncTool(
        tool_name=CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME,
        description="Custom tool with tool_type and no instruction",
        attributes=select_ai.agent.ToolAttributes(
            tool_type=select_ai.agent.ToolType.SQL,
            tool_params=select_ai.agent.SQLToolParams(
                profile_name=SQL_PROFILE_NAME
            ),
        ),
    )
    await tool.create(replace=True)
    try:
        fetched = await AsyncTool.fetch(CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME)
        log_tool_details(
            "test_3009_custom_tool_with_tool_type_without_instruction", fetched
        )
        assert fetched.tool_name == CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.instruction is not None
        assert "sql" in fetched.attributes.instruction.lower()
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        await tool.delete(force=True)


async def test_3013_custom_tool_with_tool_type_and_instruction(sql_profile):
    logger.info(
        "Validating custom tool creation with tool_type and instruction set"
    )
    tool = AsyncTool(
        tool_name=CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME,
        description="Custom tool with tool_type and instruction",
        attributes=select_ai.agent.ToolAttributes(
            tool_type=select_ai.agent.ToolType.SQL,
            tool_params=select_ai.agent.SQLToolParams(
                profile_name=SQL_PROFILE_NAME
            ),
            instruction="Use SQL profile to answer query from relational data",
        ),
    )
    await tool.create(replace=True)
    try:
        fetched = await AsyncTool.fetch(CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME)
        log_tool_details(
            "test_3009_custom_tool_with_tool_type_and_instruction", fetched
        )
        assert fetched.tool_name == CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.instruction is not None
        assert "sql" in fetched.attributes.instruction.lower()
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        await tool.delete(force=True)


async def test_3014_sql_tool_with_invalid_profile_created(neg_sql_tool):
    logger.info("Validating SQL tool with invalid profile")
    log_tool_details(
        "test_3010_sql_tool_with_invalid_profile_created", neg_sql_tool
    )
    assert neg_sql_tool.tool_name == NEG_SQL_TOOL_NAME
    assert neg_sql_tool.attributes.tool_type == select_ai.agent.ToolType.SQL
    assert (
        neg_sql_tool.attributes.tool_params.profile_name
        == "NON_EXISTENT_PROFILE"
    )


async def test_3015_rag_tool_with_invalid_profile_created(neg_rag_tool):
    logger.info("Validating RAG tool with invalid profile")
    log_tool_details(
        "test_3011_rag_tool_with_invalid_profile_created", neg_rag_tool
    )
    assert neg_rag_tool.tool_name == NEG_RAG_TOOL_NAME
    assert neg_rag_tool.attributes.tool_type == select_ai.agent.ToolType.RAG
    assert (
        neg_rag_tool.attributes.tool_params.profile_name
        == "NON_EXISTENT_RAG_PROFILE"
    )


async def test_3016_plsql_tool_with_invalid_function_created(neg_plsql_tool):
    logger.info("Validating PL/SQL tool with invalid function")
    log_tool_details(
        "test_3012_plsql_tool_with_invalid_function_created", neg_plsql_tool
    )
    assert neg_plsql_tool.tool_name == NEG_PLSQL_TOOL_NAME
    assert neg_plsql_tool.attributes.function == "NON_EXISTENT_FUNCTION"


async def test_3017_fetch_non_existent_tool():
    logger.info("Fetching non-existent tool")
    with pytest.raises(AgentToolNotFoundError) as exc:
        await AsyncTool.fetch("TOOL_DOES_NOT_EXIST")
    logger.info("Received expected error: %s", exc.value)


async def test_3018_list_invalid_regex():
    logger.info("Listing tools with invalid regex")
    with pytest.raises(Exception) as exc:
        async for _ in AsyncTool.list(tool_name_pattern="*["):
            pass
    logger.info("Received expected regex error: %s", exc.value)


async def test_3019_list_tools():
    logger.info("Listing all tools")
    tools = [tool async for tool in AsyncTool.list()]
    for tool in tools:
        if tool.tool_name in {SQL_TOOL_NAME, RAG_TOOL_NAME, PLSQL_TOOL_NAME}:
            log_tool_details("test_3015_list_tools", tool)
    tool_names = {tool.tool_name for tool in tools}
    logger.info("Tools present: %s", tool_names)
    assert len(tools) >= 3
    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


async def test_3020_create_tool_default_status_enabled(sql_profile):
    logger.info("Creating tool to validate default ENABLED status")
    tool = await AsyncTool.create_built_in_tool(
        tool_name=DEFAULT_STATUS_TOOL_NAME,
        tool_type=select_ai.agent.ToolType.SQL,
        tool_params=select_ai.agent.SQLToolParams(
            profile_name=SQL_PROFILE_NAME
        ),
    )
    try:
        await assert_tool_status(DEFAULT_STATUS_TOOL_NAME, "ENABLED")
        fetched = await AsyncTool.fetch(DEFAULT_STATUS_TOOL_NAME)
        log_tool_details(
            "test_3016_create_tool_default_status_enabled", fetched
        )
        logger.info(
            "Fetched created tool | name=%s | type=%s | profile=%s",
            fetched.tool_name,
            fetched.attributes.tool_type,
            fetched.attributes.tool_params.profile_name,
        )
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        await tool.delete(force=True)


async def test_3021_create_tool_with_enabled_false_sets_disabled(sql_profile):
    logger.info("Creating tool with enabled=False to validate DISABLED status")
    tool = AsyncTool(
        tool_name=DISABLED_TOOL_NAME,
        attributes=select_ai.agent.ToolAttributes(
            tool_type=select_ai.agent.ToolType.SQL,
            tool_params=select_ai.agent.SQLToolParams(
                profile_name=SQL_PROFILE_NAME
            ),
        ),
    )
    await tool.create(enabled=False, replace=True)
    try:
        await assert_tool_status(DISABLED_TOOL_NAME, "DISABLED")
        fetched = await AsyncTool.fetch(DISABLED_TOOL_NAME)
        log_tool_details(
            "test_3017_create_tool_with_enabled_false_sets_disabled", fetched
        )
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
    finally:
        await tool.delete(force=True)


async def test_3022_drop_tool_force_true_non_existent():
    logger.info("Validating DROP_TOOL force=True for missing tool")
    tool = AsyncTool(tool_name=DROP_FORCE_MISSING_TOOL)
    await tool.delete(force=True)
    status = await get_tool_status(DROP_FORCE_MISSING_TOOL)
    logger.info("Status after force delete on missing tool: %s", status)
    assert status is None


async def test_3023_drop_tool_force_false_non_existent_raises():
    logger.info("Validating DROP_TOOL force=False for missing tool raises")
    tool = AsyncTool(tool_name=DROP_FORCE_MISSING_TOOL)
    with pytest.raises(oracledb.Error) as exc:
        await tool.delete(force=False)
    logger.info("Received expected drop error: %s", exc.value)


async def test_3024_http_tool_created(email_credential):
    logger.info("Creating HTTP tool: %s", HTTP_TOOL_NAME)
    try:
        tool = await AsyncTool.create_http_tool(
            tool_name=HTTP_TOOL_NAME,
            credential_name=email_credential,
            endpoint=HTTP_ENDPOINT,
            description="HTTP Tool",
            replace=True,
        )
    except oracledb.DatabaseError as e:
        if "ORA-20052" in str(e):
            logger.info(
                "HTTP tool creation failed with expected backend-side error: %s",
                e,
            )
            return
        raise
    try:
        fetched = await AsyncTool.fetch(HTTP_TOOL_NAME)
        assert fetched.tool_name == HTTP_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.HTTP
        assert (
            fetched.attributes.tool_params.credential_name == email_credential
        )
        assert fetched.attributes.tool_params.endpoint == HTTP_ENDPOINT
    finally:
        logger.info("Deleting HTTP tool: %s", HTTP_TOOL_NAME)
        await tool.delete(force=True)
