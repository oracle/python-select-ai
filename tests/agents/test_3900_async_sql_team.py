import logging
import os
import uuid
from contextlib import contextmanager

import pytest
import select_ai
import select_ai.agent
from select_ai.agent import AsyncAgent, AsyncTask, AsyncTeam, AsyncTool

pytestmark = pytest.mark.anyio

# Configure file-based logging for this script run.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "test_3900_async_sql_team.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
file_handler = logging.FileHandler(LOG_FILE, mode="w")
file_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

RUN_ID = uuid.uuid4().hex.upper()
EMAIL_RECIPIENT = os.getenv("PYSAI_TEST_EMAIL_RECIPIENT")
EMAIL_SENDER = os.getenv("PYSAI_TEST_EMAIL_SENDER")
EMAIL_SMTP_HOST = os.getenv("PYSAI_TEST_EMAIL_SMTPHOST")
SQL_PROFILE_NAME = f"ASYNC_SQL_PROFILE_{RUN_ID}"
SQL_TOOL_NAME = f"ASYNC_SQL_QUERY_TOOL_{RUN_ID}"
EMAIL_TOOL_NAME = f"ASYNC_EMAIL_NOTIFICATION_TOOL_{RUN_ID}"
SQL_TASK_NAME = f"ASYNC_SQL_ANALYSIS_TASK_{RUN_ID}"
SQL_AGENT_NAME = f"ASYNC_SQL_ANALYST_AGENT_{RUN_ID}"
SQL_TEAM_NAME = f"ASYNC_SQL_DATA_TEAM_{RUN_ID}"
OCI_CREDENTIAL_NAME = f"ASYNC_SQL_TEAM_OCI_CRED_{RUN_ID}"


@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info("--- Starting test: %s ---", request.function.__name__)
    yield
    logger.info("--- Finished test: %s ---", request.function.__name__)


@contextmanager
def log_step(step):
    logger.info("START: %s", step)
    try:
        yield
        logger.info("END: %s", step)
    except Exception:
        logger.exception("FAILED: %s", step)
        raise


def log_object_details(context: str, object_type: str, obj) -> None:
    details = {"context": context, "object_type": object_type}
    attributes = getattr(obj, "attributes", None)

    if object_type == "profile":
        details.update(
            {
                "profile_name": getattr(obj, "profile_name", None),
                "description": getattr(obj, "description", None),
                "provider_type": (
                    type(getattr(attributes, "provider", None)).__name__
                    if attributes is not None
                    and getattr(attributes, "provider", None)
                    else None
                ),
                "object_count": (
                    len(getattr(attributes, "object_list", []) or [])
                    if attributes is not None
                    else None
                ),
            }
        )
    elif object_type == "agent":
        details.update(
            {
                "agent_name": getattr(obj, "agent_name", None),
                "description": getattr(obj, "description", None),
                "profile_name": (
                    getattr(attributes, "profile_name", None)
                    if attributes is not None
                    else None
                ),
                "enable_human_tool": (
                    getattr(attributes, "enable_human_tool", None)
                    if attributes is not None
                    else None
                ),
            }
        )
    elif object_type == "tool":
        details.update(
            {
                "tool_name": getattr(obj, "tool_name", None),
                "description": getattr(obj, "description", None),
                "tool_type": (
                    getattr(attributes, "tool_type", None)
                    if attributes is not None
                    else None
                ),
            }
        )
    elif object_type == "task":
        details.update(
            {
                "task_name": getattr(obj, "task_name", None),
                "description": getattr(obj, "description", None),
                "tool_count": (
                    len(getattr(attributes, "tools", []) or [])
                    if attributes is not None
                    else None
                ),
                "enable_human_tool": (
                    getattr(attributes, "enable_human_tool", None)
                    if attributes is not None
                    else None
                ),
            }
        )
    elif object_type == "team":
        details.update(
            {
                "team_name": getattr(obj, "team_name", None),
                "description": getattr(obj, "description", None),
                "process": (
                    getattr(attributes, "process", None)
                    if attributes is not None
                    else None
                ),
                "agent_count": (
                    len(getattr(attributes, "agents", []) or [])
                    if attributes is not None
                    else None
                ),
            }
        )
    else:
        details["repr"] = str(obj)

    logger.info("OBJECT_DETAILS: %s", details)


def log_credential_setup(credential_name):
    logger.info("Preparing credential | name=%s", credential_name)


async def verify_credential_exists(credential_name, expected_username=None):
    logger.info("Verifying credential exists in DB: %s", credential_name)
    async with select_ai.async_cursor() as cur:
        await cur.execute(
            """
            SELECT credential_name, username
            FROM user_credentials
            WHERE UPPER(credential_name) = UPPER(:credential_name)
            """,
            credential_name=credential_name,
        )
        row = await cur.fetchone()

    assert row is not None, f"Credential {credential_name} was not created"

    actual_name, actual_username = row
    logger.info("Verified credential | name=%s", actual_name)
    assert actual_name.upper() == credential_name.upper()
    if expected_username is not None:
        assert actual_username == expected_username


async def _cleanup_async_sql_team_objects(created) -> None:
    with log_step("Cleanup async SQL team objects"):
        if created["team"] is not None:
            try:
                logger.info("Deleting team: %s", created["team"].team_name)
                await created["team"].delete(force=True)
            except Exception:
                logger.exception(
                    "Failed to delete team: %s", created["team"].team_name
                )

        if created["task"] is not None:
            try:
                logger.info("Deleting task: %s", created["task"].task_name)
                await created["task"].delete(force=True)
            except Exception:
                logger.exception(
                    "Failed to delete task: %s", created["task"].task_name
                )

        for tool in reversed(created["tools"]):
            try:
                logger.info("Deleting tool: %s", tool.tool_name)
                await tool.delete(force=True)
            except Exception:
                logger.exception("Failed to delete tool: %s", tool.tool_name)

        if created["agent"] is not None:
            try:
                logger.info("Deleting agent: %s", created["agent"].agent_name)
                await created["agent"].delete(force=True)
            except Exception:
                logger.exception(
                    "Failed to delete agent: %s", created["agent"].agent_name
                )

        if created["profile"] is not None:
            try:
                logger.info(
                    "Deleting profile: %s", created["profile"].profile_name
                )
                await created["profile"].delete(force=True)
            except Exception:
                logger.exception(
                    "Failed to delete profile: %s",
                    created["profile"].profile_name,
                )

        for credential_name in reversed(created["credentials"]):
            try:
                logger.info("Deleting credential: %s", credential_name)
                await select_ai.async_delete_credential(
                    credential_name, force=True
                )
            except Exception:
                logger.exception(
                    "Failed to delete credential: %s", credential_name
                )


async def create_async_sql_team(test_env):
    created = {
        "team": None,
        "task": None,
        "tools": [],
        "agent": None,
        "profile": None,
        "credentials": [],
    }

    # Initialize database access required by the team and tools.
    try:
        with log_step("Initialize database and network access"):
            logger.info(
                "Using global async database pool from tests/conftest.py"
            )

        # Load OCI model and credential settings from the environment.
        oci_user_ocid = os.getenv("PYSAI_TEST_OCI_USER_OCID")
        oci_tenancy_ocid = os.getenv("PYSAI_TEST_OCI_TENANCY_OCID")
        oci_private_key = os.getenv("PYSAI_TEST_OCI_PRIVATE_KEY")
        oci_fingerprint = os.getenv("PYSAI_TEST_OCI_FINGERPRINT")
        oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
        oci_region = "us-chicago-1"
        oci_apiformat = "GENERIC"
        oci_model = "meta.llama-4-maverick-17b-128e-instruct-fp8"

        assert oci_user_ocid, "PYSAI_TEST_OCI_USER_OCID not set"
        assert oci_tenancy_ocid, "PYSAI_TEST_OCI_TENANCY_OCID not set"
        assert oci_private_key, "PYSAI_TEST_OCI_PRIVATE_KEY not set"
        assert oci_fingerprint, "PYSAI_TEST_OCI_FINGERPRINT not set"
        assert oci_compartment_id, "PYSAI_TEST_OCI_COMPARTMENT_ID not set"
        logger.info(
            "Resolved OCI configuration | credential=%s | region=%s | model=%s",
            OCI_CREDENTIAL_NAME,
            oci_region,
            oci_model,
        )

        # Create the OCI credential used by the Select AI profile.
        with log_step("Create OCI credential"):
            await select_ai.async_create_credential(
                credential={
                    "credential_name": OCI_CREDENTIAL_NAME,
                    "user_ocid": oci_user_ocid,
                    "tenancy_ocid": oci_tenancy_ocid,
                    "private_key": oci_private_key,
                    "fingerprint": oci_fingerprint,
                },
                replace=True,
            )
            created["credentials"].append(OCI_CREDENTIAL_NAME)
            await verify_credential_exists(OCI_CREDENTIAL_NAME)

        # Create the profile that backs the SQL agent's model access.
        with log_step("Create SQL profile"):
            profile = await select_ai.AsyncProfile(
                profile_name=SQL_PROFILE_NAME,
                attributes=select_ai.ProfileAttributes(
                    credential_name=OCI_CREDENTIAL_NAME,
                    provider=select_ai.OCIGenAIProvider(
                        region=oci_region,
                        oci_apiformat=oci_apiformat,
                        model=oci_model,
                        oci_compartment_id=oci_compartment_id,
                    ),
                    object_list=[{"owner": "SH"}],
                ),
                description="Profile for async SQL Agent using OCI GenAI provider.",
                replace=True,
            )
            created["profile"] = profile
            log_object_details("create_profile", "profile", profile)
            assert profile.profile_name == SQL_PROFILE_NAME

        # Create the SQL tool the task will use to query database objects.
        with log_step("Create SQL query tool"):
            sql_tool = await AsyncTool.create_sql_tool(
                tool_name=SQL_TOOL_NAME,
                profile_name=SQL_PROFILE_NAME,
                description=(
                    "Use this tool to query database tables for sales and customer info."
                ),
                replace=True,
            )
            created["tools"].append(sql_tool)
            log_object_details("create_sql_tool", "tool", sql_tool)
            fetched_sql_tool = await AsyncTool.fetch(SQL_TOOL_NAME)
            assert fetched_sql_tool.tool_name == SQL_TOOL_NAME
            assert (
                fetched_sql_tool.attributes.tool_params.profile_name
                == SQL_PROFILE_NAME
            )

        # Load SMTP settings for the email notification tool.
        email_credential_name = (
            os.getenv("PYSAI_TEST_EMAIL_CREDENTIAL_NAME")
            or f"EMAIL_CRED_{RUN_ID}"
        )
        email_username = os.getenv("PYSAI_TEST_EMAIL_CRED_USERNAME")
        email_password = os.getenv("PYSAI_TEST_EMAIL_CRED_PASSWORD")

        assert email_username, "PYSAI_TEST_EMAIL_CRED_USERNAME not set"
        assert email_password, "PYSAI_TEST_EMAIL_CRED_PASSWORD not set"
        log_credential_setup(email_credential_name)

        # Create the SMTP credential used by the notification tool.
        with log_step("Create email credential"):
            await select_ai.async_create_credential(
                credential={
                    "credential_name": email_credential_name,
                    "username": email_username,
                    "password": email_password,
                },
                replace=True,
            )
            created["credentials"].append(email_credential_name)
            await verify_credential_exists(
                email_credential_name, expected_username=email_username
            )

        # Create the built-in email notification tool.
        with log_step("Create email notification tool"):
            email_tool = await AsyncTool.create_email_notification_tool(
                tool_name=EMAIL_TOOL_NAME,
                credential_name=email_credential_name,
                recipient=EMAIL_RECIPIENT,
                sender=EMAIL_SENDER,
                smtp_host=EMAIL_SMTP_HOST,
                description="Send notification emails for SQL insights",
                replace=True,
            )
            created["tools"].append(email_tool)
            log_object_details("create_email_tool", "tool", email_tool)
            fetched_email_tool = await AsyncTool.fetch(EMAIL_TOOL_NAME)
            assert fetched_email_tool.tool_name == EMAIL_TOOL_NAME
            assert (
                fetched_email_tool.attributes.tool_params.credential_name
                == email_credential_name
            )

        # Create the task that combines SQL analysis with email delivery.
        with log_step("Create SQL analysis task"):
            task = AsyncTask(
                task_name=SQL_TASK_NAME,
                attributes=select_ai.agent.TaskAttributes(
                    instruction=(
                        "Answer the user query by querying the database: {query}. "
                        "After you produce the answer, send a concise summary of the findings "
                        "to the analytics stakeholders using the "
                        f"{EMAIL_TOOL_NAME}. "
                        "Include the SQL results and any key metrics in the email body."
                    ),
                    tools=[SQL_TOOL_NAME, EMAIL_TOOL_NAME],
                ),
            )
            await task.create(enabled=True, replace=True)
            created["task"] = task
            log_object_details("create_task", "task", task)
            fetched_task = await AsyncTask.fetch(SQL_TASK_NAME)
            assert fetched_task.task_name == SQL_TASK_NAME
            assert set(fetched_task.attributes.tools) == {
                SQL_TOOL_NAME,
                EMAIL_TOOL_NAME,
            }

        # Create the agent that will execute the SQL analysis task.
        with log_step("Create SQL analyst agent"):
            agent = AsyncAgent(
                agent_name=SQL_AGENT_NAME,
                attributes=select_ai.agent.AgentAttributes(
                    profile_name=SQL_PROFILE_NAME,
                    role="You are a data analyst that translates natural language to SQL.",
                    enable_human_tool=False,
                ),
            )
            await agent.create(enabled=True, replace=True)
            created["agent"] = agent
            log_object_details("create_agent", "agent", agent)
            fetched_agent = await AsyncAgent.fetch(SQL_AGENT_NAME)
            assert fetched_agent.agent_name == SQL_AGENT_NAME
            assert fetched_agent.attributes.profile_name == SQL_PROFILE_NAME
            assert fetched_agent.attributes.enable_human_tool is False

        # Create the team that wires the agent to the task.
        with log_step("Create SQL data team"):
            team = AsyncTeam(
                team_name=SQL_TEAM_NAME,
                attributes=select_ai.agent.TeamAttributes(
                    agents=[{"name": SQL_AGENT_NAME, "task": SQL_TASK_NAME}],
                    process="sequential",
                ),
            )
            await team.create(replace=True, enabled=True)
            created["team"] = team
            log_object_details("create_team", "team", team)
            fetched_team = await AsyncTeam.fetch(SQL_TEAM_NAME)
            assert fetched_team.team_name == SQL_TEAM_NAME
            assert fetched_team.attributes.process == "sequential"
            assert fetched_team.attributes.agents == [
                {"name": SQL_AGENT_NAME, "task": SQL_TASK_NAME}
            ]

            yield team
    finally:
        await _cleanup_async_sql_team_objects(created)


@pytest.fixture(scope="module")
async def async_sql_team(async_connect, test_env, allow_network_acl):
    async for team in create_async_sql_team(test_env):
        yield team


async def test_async_sql_team_runs(async_sql_team):
    # Run the team with a sample prompt and verify a response is returned.
    with log_step("Run async SQL team"):
        conversation_id = str(uuid.uuid4())
        prompt = "List tables in the SH schema?"
        logger.info(
            "Running team | team=%s | conversation_id=%s | prompt=%s",
            async_sql_team.team_name,
            conversation_id,
            prompt,
        )
        response = await async_sql_team.run(
            prompt=prompt,
            params={"conversation_id": conversation_id},
        )
        logger.info("Agent Response: %s", response)
        assert response is not None
        assert isinstance(response, str)
        assert len(response.strip()) > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
