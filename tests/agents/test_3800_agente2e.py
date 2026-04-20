# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
import os
import time
import uuid
from contextlib import contextmanager

import pytest
import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
    Tool,
    ToolAttributes,
    ToolParams,
)

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------


# Path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3800_agente2e.log")
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

EMAIL_RECIPIENT = os.getenv("PYSAI_TEST_EMAIL_RECIPIENT")
EMAIL_SENDER = os.getenv("PYSAI_TEST_EMAIL_SENDER")
EMAIL_SMTP_HOST = os.getenv("PYSAI_TEST_EMAIL_SMTPHOST")


@contextmanager
def log_step(step):
    logger.info("START: %s", step)
    start = time.time()
    try:
        yield
        logger.info("END: %s (%.2fs)", step, time.time() - start)
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


def verify_credential_exists(credential_name, expected_username=None):
    logger.info("Verifying credential exists in DB: %s", credential_name)

    with select_ai.cursor() as cur:
        cur.execute(
            """
            SELECT credential_name, username
            FROM user_credentials
            WHERE UPPER(credential_name) = UPPER(:credential_name)
            """,
            credential_name=credential_name,
        )
        row = cur.fetchone()

    assert row is not None, f"Credential {credential_name} was not created"

    actual_name, actual_username = row
    logger.info("Verified credential | name=%s", actual_name)
    assert actual_name.upper() == credential_name.upper()
    if expected_username is not None:
        assert actual_username == expected_username


def _decode_history_rows(rows):
    decoded_rows = []
    for row in rows:
        decoded_row = []
        for value in row:
            if hasattr(value, "read"):
                decoded_row.append(value.read())
            else:
                decoded_row.append(value)
        decoded_rows.append(tuple(decoded_row))
    return decoded_rows


@pytest.fixture(scope="module")
def openai_cred(connect):
    api_key = os.getenv("PYSAI_TEST_OPENAI_API_KEY")
    assert api_key, "PYSAI_TEST_OPENAI_API_KEY not set"
    cred_name = "OPENAI_CRED"

    log_credential_setup(cred_name)

    select_ai.create_credential(
        credential={
            "credential_name": cred_name,
            "username": "openai",
            "password": api_key,
        },
        replace=True,
    )

    verify_credential_exists(cred_name, expected_username="openai")
    return cred_name


@pytest.fixture(scope="module")
def email_cred(connect):
    smtp_username = os.getenv("PYSAI_TEST_EMAIL_CRED_USERNAME")
    smtp_password = os.getenv("PYSAI_TEST_EMAIL_CRED_PASSWORD")

    assert smtp_username, "PYSAI_TEST_EMAIL_CRED_USERNAME not set"
    assert smtp_password, "PYSAI_TEST_EMAIL_CRED_PASSWORD not set"
    cred_name = "EMAIL_CRED"

    log_credential_setup(cred_name)

    select_ai.create_credential(
        credential={
            "credential_name": cred_name,
            "username": smtp_username,
            "password": smtp_password,
        },
        replace=True,
    )

    verify_credential_exists(cred_name, expected_username=smtp_username)
    return cred_name


# ----------------------------------------------------------------------
# MAIN TEST
# ----------------------------------------------------------------------


def test_3800_agent_end_to_end(
    connect,
    profile_attributes,
    openai_cred,
    email_cred,
    allow_network_acl,
):
    """
    End-to-end Select AI Agent integration test.

    """

    # -------------------------------
    # PROFILE
    # -------------------------------
    logger.info("Starting End-to-End Agent Test")
    logger.info(
        "Resolved credential fixtures | openai=%s | email=%s",
        openai_cred,
        email_cred,
    )
    created = {
        "team": None,
        "task": None,
        "tools": [],
        "agent": None,
        "profile": None,
    }

    # ---------------- PROFILE ----------------

    oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
    assert oci_compartment_id, "PYSAI_TEST_OCI_COMPARTMENT_ID not set"

    profile_attributes.provider.oci_compartment_id = oci_compartment_id

    try:
        profile = select_ai.Profile(
            profile_name="GEN1_PROFILE",
            attributes=profile_attributes,
            replace=True,
        )
        created["profile"] = profile
        log_object_details("create_profile", "profile", profile)

        # -------------------------------
        # AGENT
        # -------------------------------
        with log_step("Create agent"):
            agent = Agent(
                agent_name="CustomerAgent",
                attributes=AgentAttributes(
                    profile_name="GEN1_PROFILE",
                    role="You are an experienced customer agent handling returns.",
                    enable_human_tool=False,
                ),
            )
            agent.create(replace=True)
            created["agent"] = agent
            log_object_details("create_agent", "agent", agent)

            assert agent.agent_name == "CustomerAgent"
            assert agent.attributes.enable_human_tool is False

        # -------------------------------
        # TOOLS
        # -------------------------------
        with log_step("Create tools"):
            websearch_tool = Tool(
                tool_name="Websearch",
                attributes=ToolAttributes(
                    tool_type="WEBSEARCH",
                    instruction="Use this tool to find the current price of a product from a URL.",
                    tool_params=ToolParams(credential_name=openai_cred),
                ),
            )
            websearch_tool.create(replace=True)
            created["tools"].append(websearch_tool)
            log_object_details("create_websearch_tool", "tool", websearch_tool)
            fetched_websearch_tool = Tool.fetch("Websearch")
            logger.info(
                "Verified fetched websearch tool credential | tool=%s | credential=%s",
                fetched_websearch_tool.tool_name,
                fetched_websearch_tool.attributes.tool_params.credential_name,
            )
            assert (
                fetched_websearch_tool.attributes.tool_params.credential_name
                == openai_cred
            )

            # Email notification tool
            email_tool = Tool(
                tool_name="Email",
                attributes=ToolAttributes(
                    tool_type="NOTIFICATION",
                    tool_params=ToolParams(
                        credential_name=email_cred,
                        notification_type="EMAIL",
                        recipient=EMAIL_RECIPIENT,
                        sender=EMAIL_SENDER,
                        smtp_host=EMAIL_SMTP_HOST,
                    ),
                ),
            )
            email_tool.create(replace=True)
            created["tools"].append(email_tool)
            log_object_details("create_email_tool", "tool", email_tool)
            fetched_email_tool = Tool.fetch("Email")
            logger.info(
                "Verified fetched email tool credential | tool=%s | credential=%s",
                fetched_email_tool.tool_name,
                fetched_email_tool.attributes.tool_params.credential_name,
            )
            assert (
                fetched_email_tool.attributes.tool_params.credential_name
                == email_cred
            )

            assert Tool("Email") is not None
            assert (
                websearch_tool.attributes.tool_params.credential_name
                == openai_cred
            )
            assert (
                email_tool.attributes.tool_params.credential_name == email_cred
            )

        # -------------------------------
        # TASK
        # -------------------------------
        with log_step("Create task"):
            task = Task(
                task_name="Return_And_Price_Match",
                attributes=TaskAttributes(
                    instruction=(
                        "Process a product return request from a customer. "
                        "1. Ask customer the reason for return (price match or defective). "
                        "2. If price match: "
                        "   a. Request customer to provide a price match link. "
                        "   b. Use websearch tool to get the price for that price match link"
                        "   c. Ask customer if they want a refund and specify how much refund. "
                        "   d. Send email notification only if customer accepts the refund. "
                        "3. If defective: "
                        "   a. Process the defective return."
                    ),
                    tools=["Websearch", "Email"],
                    enable_human_tool=False,
                ),
            )
            task.create(replace=True)
            created["task"] = task
            log_object_details("create_task", "task", task)

            assert task.task_name == "Return_And_Price_Match"
            assert set(task.attributes.tools) == {"Websearch", "Email"}
            assert task.attributes.enable_human_tool is False

        assert task.task_name == "Return_And_Price_Match"
        assert set(task.attributes.tools) == {"Websearch", "Email"}

        # -------------------------------
        # TEAM
        # -------------------------------
        with log_step("Create team"):
            team = Team(
                team_name="ReturnAgency",
                attributes=TeamAttributes(
                    agents=[
                        {
                            "name": "CustomerAgent",
                            "task": "Return_And_Price_Match",
                        }
                    ],
                    process="sequential",
                ),
            )
            team.create(enabled=True, replace=True)
            created["team"] = team
            log_object_details("create_team", "team", team)

            assert team.team_name == "ReturnAgency"

        # -------------------------------
        # RUN CONVERSATION
        # -------------------------------
        with log_step("Run agent conversation"):
            conversation_id = str(uuid.uuid4())

            prompts = [
                "I want to return an office chair",
                "The price when I bought it is 100. But I found a cheaper price",
                "Here is the price match link 'https://www.ikea.com/us/en/p/stefan-chair-brown-black-00211088/'",
                "Yes, I would like to proceed with a refund",
            ]

            for idx, prompt in enumerate(prompts, start=1):
                logger.info("USER %d: %s", idx, prompt)

                response = team.run(
                    prompt=prompt,
                    params={"conversation_id": conversation_id},
                )

                print(f"\nAGENT RESPONSE {idx}:\n{response}\n")
                logger.info("AGENT RESPONSE %d: %s", idx, response)

                assert response is not None
                assert isinstance(response, (str, dict))

                if isinstance(response, dict):
                    assert response

            with select_ai.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM user_ai_agent_tool_history
                    """
                )
                tool_history = cur.fetchall()

            decoded_tool_history = _decode_history_rows(tool_history)

            logger.info(
                "Tool history rows fetched: %d", len(decoded_tool_history)
            )

            assert decoded_tool_history
    finally:
        with log_step("Cleanup sync e2e objects"):
            if created["team"] is not None:
                logger.info("Deleting team: %s", created["team"].team_name)
                created["team"].delete(force=True)

            if created["task"] is not None:
                logger.info("Deleting task: %s", created["task"].task_name)
                created["task"].delete(force=True)

            for tool in reversed(created["tools"]):
                logger.info("Deleting tool: %s", tool.tool_name)
                tool.delete(force=True)

            if created["agent"] is not None:
                logger.info("Deleting agent: %s", created["agent"].agent_name)
                created["agent"].delete(force=True)

            if created["profile"] is not None:
                logger.info(
                    "Deleting profile: %s", created["profile"].profile_name
                )
                created["profile"].delete(force=True)
