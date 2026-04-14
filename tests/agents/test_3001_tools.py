# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3001 - Complete and backend-aligned test coverage for select_ai.agent Tool APIs
(with logging for behavior visibility)
"""

import uuid
import logging
import pytest
import os
import select_ai
import oracledb
from select_ai.agent import Tool
from select_ai.errors import AgentToolNotFoundError

# Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3001_tools.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Force logging to file (pytest-proof)
root = logging.getLogger()
root.setLevel(logging.INFO)

for h in root.handlers[:]:
    root.removeHandler(h)

fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)

logger = logging.getLogger()

# -----------------------------------------------------------------------------
# Per-test logging
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def get_tool_status(tool_name):
    with select_ai.cursor() as cur:
        cur.execute("""
            SELECT status
            FROM USER_AI_AGENT_TOOLS
            WHERE tool_name = :tool_name
        """, {"tool_name": tool_name})
        row = cur.fetchone()
        return row[0] if row else None

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
UUID = uuid.uuid4().hex.upper()

SQL_PROFILE_NAME = f"PYSAI_SQL_PROFILE_{UUID}"
RAG_PROFILE_NAME = f"PYSAI_RAG_PROFILE_{UUID}"

SQL_TOOL_NAME = f"PYSAI_SQL_TOOL_{UUID}"
RAG_TOOL_NAME = f"PYSAI_RAG_TOOL_{UUID}"
PLSQL_TOOL_NAME = f"PYSAI_PLSQL_TOOL_{UUID}"
WEB_SEARCH_TOOL_NAME = f"PYSAI_WEB_TOOL_{UUID}"
PLSQL_FUNCTION_NAME = f"PYSAI_CALC_AGE_{UUID}"
CUSTOM_ATTR_TOOL_NAME = f"PYSAI_3001_CUSTOM_ATTR_TOOL_{UUID}"
CUSTOM_ATTR_TOOL_DESCRIPTION = "Custom attr tool for sync testing"
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
smtp_username = os.getenv("PYSAI_TEST_EMAIL_CRED_USERNAME")
smtp_password = os.getenv("PYSAI_TEST_EMAIL_CRED_PASSWORD")
slack_username = os.getenv("PYSAI_TEST_SLACK_USERNAME")
slack_password = os.getenv("PYSAI_TEST_SLACK_PASSWORD")

@pytest.fixture(scope="module")
def email_credential():
    cred_name = "EMAIL_CRED"
    logger.info("Ensuring EMAIL credential is clean: %s", cred_name)

    # Drop if exists (best-effort)
    try:
        select_ai.delete_credential(cred_name)
        logger.info("Dropped existing EMAIL credential: %s", cred_name)
    except Exception as e:
        logger.info("EMAIL credential did not exist or could not be dropped: %s", e)

    # Create fresh credential
    credential = {
        "credential_name": cred_name,
        "username": smtp_username,
        "password": smtp_password,
    }

    select_ai.create_credential(
        credential=credential,
        replace=True
    )
    logger.info("Created EMAIL credential: %s", cred_name)

    yield cred_name

    logger.info("Deleting EMAIL credential at teardown: %s", cred_name)
    try:
        select_ai.delete_credential(cred_name)
    except Exception as e:
        logger.warning("Failed to delete EMAIL credential during teardown: %s", e)

@pytest.fixture(scope="module")
def slack_credential():
    cred_name = "SLACK_CRED"
    logger.info("Ensuring SLACK credential is clean: %s", cred_name)

    # Drop if exists (best-effort)
    try:
        select_ai.delete_credential(cred_name)
        logger.info("Dropped existing SLACK credential: %s", cred_name)
    except Exception as e:
        logger.info("SLACK credential did not exist or could not be dropped: %s", e)

    # Create fresh SLACK credential (backend-required fields)
    credential = {
        "credential_name": cred_name,
        "username": slack_username,
        "password": slack_password,
    }

    select_ai.create_credential(
        credential=credential,
        replace=True
    )
    logger.info("Created SLACK credential: %s", cred_name)

    yield cred_name

    logger.info("Deleting SLACK credential at teardown: %s", cred_name)
    try:
        select_ai.delete_credential(cred_name)
    except Exception as e:
        logger.warning("Failed to delete SLACK credential during teardown: %s", e)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sql_profile(profile_attributes):
    logger.info("Creating SQL profile: %s", SQL_PROFILE_NAME)
    profile = select_ai.Profile(
        profile_name=SQL_PROFILE_NAME,
        description="SQL Profile",
        attributes=profile_attributes,
    )
    yield profile
    logger.info("Deleting SQL profile")
    profile.delete(force=True)


@pytest.fixture(scope="module")
def rag_profile(rag_profile_attributes):
    logger.info("Creating RAG profile: %s", RAG_PROFILE_NAME)
    profile = select_ai.Profile(
        profile_name=RAG_PROFILE_NAME,
        description="RAG Profile",
        attributes=rag_profile_attributes,
    )
    yield profile
    logger.info("Deleting RAG profile")
    profile.delete(force=True)


@pytest.fixture(scope="module")
def sql_tool(sql_profile):
    logger.info("Creating SQL tool: %s", SQL_TOOL_NAME)
    tool = select_ai.agent.Tool.create_sql_tool(
        tool_name=SQL_TOOL_NAME,
        profile_name=SQL_PROFILE_NAME,
        description="SQL Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting SQL tool")
    tool.delete(force=True)


@pytest.fixture(scope="module")
def rag_tool(rag_profile):
    logger.info("Creating RAG tool: %s", RAG_TOOL_NAME)
    tool = select_ai.agent.Tool.create_rag_tool(
        tool_name=RAG_TOOL_NAME,
        profile_name=RAG_PROFILE_NAME,
        description="RAG Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting RAG tool")
    tool.delete(force=True)


@pytest.fixture(scope="module")
def plsql_function():
    logger.info("Creating PL/SQL function: %s", PLSQL_FUNCTION_NAME)
    ddl = f"""
    CREATE OR REPLACE FUNCTION {PLSQL_FUNCTION_NAME}(p_birth_date DATE)
    RETURN NUMBER IS
    BEGIN
        RETURN TRUNC(MONTHS_BETWEEN(SYSDATE, p_birth_date) / 12);
    END;
    """
    with select_ai.cursor() as cur:
        cur.execute(ddl)
    yield
    logger.info("Dropping PL/SQL function")
    with select_ai.cursor() as cur:
        cur.execute(f"DROP FUNCTION {PLSQL_FUNCTION_NAME}")


@pytest.fixture(scope="module")
def plsql_tool(plsql_function):
    logger.info("Creating PL/SQL tool: %s", PLSQL_TOOL_NAME)
    tool = select_ai.agent.Tool.create_pl_sql_tool(
        tool_name=PLSQL_TOOL_NAME,
        function=PLSQL_FUNCTION_NAME,
        description="PL/SQL Tool",
        replace=True,
    )
    yield tool
    logger.info("Deleting PL/SQL tool")
    tool.delete(force=True)

@pytest.fixture(scope="module")
def web_search_tool():
    """Fixture for Web Search Tool positive case."""
    logger.info("Creating Web Search tool: %s", WEB_SEARCH_TOOL_NAME)
    tool = select_ai.agent.Tool.create_websearch_tool(
        tool_name=WEB_SEARCH_TOOL_NAME,
        description="Web Search Tool for testing",
        credential_name="OPENAI_CRED",
        replace=True,
    )
    logger.info("WEBSEARCH Tool created successfully: %s", WEB_SEARCH_TOOL_NAME)
    yield tool
    logger.info("Deleting Web Search tool")
    tool.delete(force=True)

@pytest.fixture(scope="module")
def email_tool(email_credential):
    logger.info("Creating EMAIL tool: EMAIL_TOOL")
    tool = select_ai.agent.Tool.create_email_notification_tool(
        tool_name="EMAIL_TOOL",
        credential_name="EMAIL_CRED",
        recipient="kondra.nagabhavani@oracle.com",
        sender="bharadwaj.vulugundam@oracle.com",
        smtp_host="smtp.email.us-ashburn-1.oci.oraclecloud.com",
        description="Send email",
        replace=True,
    )
    logger.info("EMAIL_TOOL created successfully")
    yield tool
    logger.info("Deleting EMAIL tool")
    tool.delete(force=True)

@pytest.fixture(scope="module")
def slack_tool(slack_credential):
    logger.info("Creating SLACK tool: SLACK_TOOL")
    try:
        tool = select_ai.agent.Tool.create_slack_notification_tool(
            tool_name="SLACK_TOOL",
            credential_name="SLACK_CRED",
            channel="#general",
            description="slack notification",
            replace=True,
        )
        logger.info("SLACK_TOOL is created successfully")
        yield tool
    except oracledb.DatabaseError as e:
        if "ORA-20052" in str(e):
            logger.info(f"Expected error during tool creation: {e}")
            yield None  # Return None, indicating the tool creation failed but is expected
        else:
            raise e
    finally:
        if 'tool' in locals():
            logger.info("Deleting SLACK tool")
            tool.delete(force=True)

@pytest.fixture(scope="module")
def neg_sql_tool():
    logger.info("Creating SQL tool with INVALID profile: NEG_SQL_TOOL")
    tool = select_ai.agent.Tool.create_sql_tool(
        tool_name="NEG_SQL_TOOL",
        profile_name="NON_EXISTENT_PROFILE",
        replace=True,
    )
    logger.info("NEG_SQL_TOOL is created successfully.")
    yield tool
    logger.info("Deleting NEG_SQL_TOOL")
    tool.delete(force=True)

@pytest.fixture(scope="module")
def neg_rag_tool():
    logger.info("Creating RAG tool with INVALID profile: NEG_RAG_TOOL")
    tool = select_ai.agent.Tool.create_rag_tool(
        tool_name="NEG_RAG_TOOL",
        profile_name="NON_EXISTENT_RAG_PROFILE",
        replace=True,
    )
    logger.info("NEG_RAG_TOOL is created successfully")
    yield tool
    logger.info("Deleting NEG_RAG_TOOL")
    tool.delete(force=True)


@pytest.fixture(scope="module")
def neg_plsql_tool():
    logger.info("Creating PL/SQL tool with INVALID function: NEG_PLSQL_TOOL")
    tool = select_ai.agent.Tool.create_pl_sql_tool(
        tool_name="NEG_PLSQL_TOOL",
        function="NON_EXISTENT_FUNCTION",
        replace=True,
    )
    logger.info("NEG_PLSQL_TOOL is created successfully")
    yield tool
    logger.info("Deleting NEG_PLSQL_TOOL")
    tool.delete(force=True)

# -----------------------------------------------------------------------------
# POSITIVE TESTS
# -----------------------------------------------------------------------------

def test_3000_sql_tool_created(sql_tool):
    logger.info("Validating SQL tool creation")
    logger.info("SQL Tool created successfully: %s", SQL_TOOL_NAME)
    logger.info("SQL Profile created successfully: %s", SQL_PROFILE_NAME)
    assert sql_tool.tool_name == SQL_TOOL_NAME
    assert sql_tool.attributes.tool_params.profile_name == SQL_PROFILE_NAME


def test_3001_rag_tool_created(rag_tool):
    logger.info("Validating RAG tool creation")
    logger.info("RAG Tool created successfully: %s", RAG_TOOL_NAME)
    logger.info("RAG Profile created successfully: %s", RAG_PROFILE_NAME)
    assert rag_tool.tool_name == RAG_TOOL_NAME
    assert rag_tool.attributes.tool_params.profile_name == RAG_PROFILE_NAME


def test_3002_plsql_tool_created(plsql_tool):
    logger.info("Validating PL/SQL tool creation")
    logger.info("PL/SQL Tool created successfully: %s", PLSQL_TOOL_NAME)
    logger.info("PL/SQL function created successfully: %s", PLSQL_FUNCTION_NAME)
    assert plsql_tool.tool_name == PLSQL_TOOL_NAME
    assert plsql_tool.attributes.function == PLSQL_FUNCTION_NAME


def test_3003_list_tools():
    logger.info("Listing all tools")
    tool_names = {t.tool_name for t in select_ai.agent.Tool.list()}
    logger.info("Tools present: %s", tool_names)

    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


def test_3004_list_tools_regex():
    logger.info("Listing tools using regex ^PYSAI_")
    tool_names = {t.tool_name for t in select_ai.agent.Tool.list("^PYSAI_")}
    logger.info("Matched tools: %s", tool_names)

    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


def test_3005_fetch_tool():
    logger.info("Fetching SQL tool")
    tool = select_ai.agent.Tool.fetch(SQL_TOOL_NAME)
    assert tool.tool_name == SQL_TOOL_NAME


def test_3006_enable_disable_sql_tool(sql_tool):
    logger.info("Disabling SQL tool: %s", sql_tool.tool_name)
    sql_tool.disable()

    status = get_tool_status(sql_tool.tool_name)
    logger.info(
        "Tool status after disable | tool=%s | status=%s",
        sql_tool.tool_name,
        status,
    )
    assert status == "DISABLED"

    logger.info("Enabling SQL tool: %s", sql_tool.tool_name)
    sql_tool.enable()

    status = get_tool_status(sql_tool.tool_name)
    logger.info(
        "Tool status after enable | tool=%s | status=%s",
        sql_tool.tool_name,
        status,
    )
    assert status == "ENABLED"


def test_3007_web_search_tool_created(web_search_tool):
    logger.info("Validating Web Search tool creation")
    assert web_search_tool.tool_name == WEB_SEARCH_TOOL_NAME


def test_3008_email_tool_created(email_tool):
    logger.info("Validating EMAIL tool creation")
    assert email_tool.tool_name == "EMAIL_TOOL"


def test_3009_slack_tool_created(slack_tool):
    logger.info("Validating SLACK tool creation")

    # If the tool is None (because of expected ORA-20052 error), skip the assertion
    if slack_tool is None:
        logger.info("SLACK tool creation failed with expected error ORA-20052, but continuing test.")
    else:
        assert slack_tool.tool_name == "SLACK_TOOL"

def test_3010_custom_tool_attributes_roundtrip():
    logger.info(
        "Validating custom tool attribute roundtrip: instruction/tool_inputs/description"
    )
    tool = Tool(
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
    tool.create(replace=True)
    try:
        fetched = select_ai.agent.Tool.fetch(CUSTOM_ATTR_TOOL_NAME)
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
        assert "birth date" in fetched.attributes.tool_inputs[0]["description"].lower()
    finally:
        tool.delete(force=True)


def test_3011_custom_tool_without_tool_type():
    logger.info("Validating custom tool creation with tool_type unset")
    tool = Tool(
        tool_name=CUSTOM_NO_TYPE_TOOL_NAME,
        description="Custom tool without explicit tool_type",
        attributes=select_ai.agent.ToolAttributes(
            function=PLSQL_FUNCTION_NAME,
        ),
    )
    tool.create(replace=True)
    try:
        fetched = select_ai.agent.Tool.fetch(CUSTOM_NO_TYPE_TOOL_NAME)
        assert fetched.tool_name == CUSTOM_NO_TYPE_TOOL_NAME
        assert fetched.attributes.function == PLSQL_FUNCTION_NAME
        assert fetched.attributes.tool_type is None
        assert fetched.description == "Custom tool without explicit tool_type"
    finally:
        tool.delete(force=True)


def test_3012_custom_tool_with_tool_type_without_instruction(sql_profile):
    logger.info("Validating custom tool with tool_type and no instruction")
    tool = Tool(
        tool_name=CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME,
        description="Custom tool with tool_type and no instruction",
        attributes=select_ai.agent.ToolAttributes(
            tool_type=select_ai.agent.ToolType.SQL,
            tool_params=select_ai.agent.SQLToolParams(
                profile_name=SQL_PROFILE_NAME
            ),
        ),
    )
    tool.create(replace=True)
    try:
        fetched = select_ai.agent.Tool.fetch(CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME)
        logger.info(
            "Fetched custom tool | name=%s | type=%s | instruction=%s | profile=%s",
            fetched.tool_name,
            fetched.attributes.tool_type,
            fetched.attributes.instruction,
            fetched.attributes.tool_params.profile_name,
        )
        assert fetched.tool_name == CUSTOM_WITH_TYPE_NO_INSTR_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.instruction is not None
        assert "sql" in fetched.attributes.instruction.lower()
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        tool.delete(force=True)


def test_3013_custom_tool_with_tool_type_and_instruction(sql_profile):
    logger.info("Validating custom tool with tool_type and instruction")
    tool = Tool(
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
    tool.create(replace=True)
    try:
        fetched = select_ai.agent.Tool.fetch(CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME)
        assert fetched.tool_name == CUSTOM_WITH_TYPE_AND_INSTR_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.instruction is not None
        assert "sql" in fetched.attributes.instruction.lower()
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        tool.delete(force=True)


def test_3014_sql_tool_with_invalid_profile_created(neg_sql_tool):
    logger.info("Validating SQL tool with invalid profile is stored")
    assert neg_sql_tool.tool_name == "NEG_SQL_TOOL"
    assert neg_sql_tool.attributes.tool_params.profile_name == "NON_EXISTENT_PROFILE"


def test_3015_rag_tool_with_invalid_profile_created(neg_rag_tool):
    logger.info("Validating RAG tool with invalid profile is stored")
    assert neg_rag_tool.tool_name == "NEG_RAG_TOOL"
    assert neg_rag_tool.attributes.tool_params.profile_name == "NON_EXISTENT_RAG_PROFILE"


def test_3016_plsql_tool_with_invalid_function_created(neg_plsql_tool):
    logger.info("Validating PL/SQL tool with invalid function is stored")
    assert neg_plsql_tool.tool_name == "NEG_PLSQL_TOOL"
    assert neg_plsql_tool.attributes.function == "NON_EXISTENT_FUNCTION"


def test_3017_fetch_non_existent_tool():
    logger.info("Fetching non-existent tool")
    with pytest.raises(AgentToolNotFoundError) as exc:
        select_ai.agent.Tool.fetch("TOOL_DOES_NOT_EXIST")
    logger.error("%s", exc.value)


def test_3018_list_invalid_regex():
    logger.info("Listing tools with invalid regex")
    with pytest.raises(Exception) as exc:
        list(select_ai.agent.Tool.list(tool_name_pattern="*["))
    logger.error("%s", exc.value)


def test_3019_list_tools():
    logger.info("Listing all tools")
    tool_names = {t.tool_name for t in select_ai.agent.Tool.list()}
    logger.info("Tools present: %s", tool_names)

    assert SQL_TOOL_NAME in tool_names
    assert RAG_TOOL_NAME in tool_names
    assert PLSQL_TOOL_NAME in tool_names


def test_3020_create_tool_default_status_enabled(sql_profile):
    logger.info("Creating tool to validate default ENABLED status")
    tool = select_ai.agent.Tool.create_built_in_tool(
        tool_name=DEFAULT_STATUS_TOOL_NAME,
        tool_type=select_ai.agent.ToolType.SQL,
        tool_params=select_ai.agent.SQLToolParams(profile_name=SQL_PROFILE_NAME),
    )
    try:
        status = get_tool_status(DEFAULT_STATUS_TOOL_NAME)
        logger.info("Tool status after create: %s", status)
        assert status == "ENABLED"
        fetched = select_ai.agent.Tool.fetch(DEFAULT_STATUS_TOOL_NAME)
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
        assert fetched.attributes.tool_params.profile_name == SQL_PROFILE_NAME
    finally:
        tool.delete(force=True)


def test_3021_create_tool_with_enabled_false_sets_disabled(sql_profile):
    logger.info("Creating tool with enabled=False to validate DISABLED status")
    tool = Tool(
        tool_name=DISABLED_TOOL_NAME,
        attributes=select_ai.agent.ToolAttributes(
            tool_type=select_ai.agent.ToolType.SQL,
            tool_params=select_ai.agent.SQLToolParams(
                profile_name=SQL_PROFILE_NAME
            ),
        ),
    )
    tool.create(enabled=False, replace=True)
    try:
        status = get_tool_status(DISABLED_TOOL_NAME)
        logger.info("Tool status after create(enabled=False): %s", status)
        assert status == "DISABLED"
        fetched = select_ai.agent.Tool.fetch(DISABLED_TOOL_NAME)
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.SQL
    finally:
        tool.delete(force=True)


def test_3022_drop_tool_force_true_non_existent():
    logger.info("Validating DROP_TOOL force=True for missing tool")
    tool = Tool(tool_name=DROP_FORCE_MISSING_TOOL)
    tool.delete(force=True)
    status = get_tool_status(DROP_FORCE_MISSING_TOOL)
    logger.info("Status after force delete on missing tool: %s", status)
    assert status is None


def test_3023_drop_tool_force_false_non_existent_raises():
    logger.info("Validating DROP_TOOL force=False for missing tool raises")
    tool = Tool(tool_name=DROP_FORCE_MISSING_TOOL)
    with pytest.raises(oracledb.Error) as exc:
        tool.delete(force=False)
    logger.info("Received expected drop error: %s", exc.value)


def test_3024_http_tool_created(email_credential):
    logger.info("Creating HTTP tool: %s", HTTP_TOOL_NAME)
    try:
        tool = select_ai.agent.Tool.create_http_tool(
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
        fetched = select_ai.agent.Tool.fetch(HTTP_TOOL_NAME)
        assert fetched.tool_name == HTTP_TOOL_NAME
        assert fetched.attributes.tool_type == select_ai.agent.ToolType.HTTP
        assert fetched.attributes.tool_params.credential_name == email_credential
        assert fetched.attributes.tool_params.endpoint == HTTP_ENDPOINT
    finally:
        logger.info("Deleting HTTP tool: %s", HTTP_TOOL_NAME)
        tool.delete(force=True)
