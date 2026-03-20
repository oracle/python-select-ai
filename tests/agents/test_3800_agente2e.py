# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import uuid
import time
import os
import logging
import pytest
from contextlib import contextmanager

import select_ai
from select_ai.agent import (
    Agent,
    AgentAttributes,
    Task,
    TaskAttributes,
    Team,
    TeamAttributes,
    Tool,
    ToolParams,
    ToolAttributes,
)

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------


# Path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
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


def _safe_dict(obj):
    if obj is None:
        return None
    if hasattr(obj, "dict"):
        try:
            return obj.dict(exclude_null=False)
        except TypeError:
            return obj.dict()
    return str(obj)


def log_object_details(context: str, object_type: str, obj) -> None:
    details = {"context": context, "object_type": object_type}

    if object_type == "profile":
        details.update(
            {
                "profile_name": getattr(obj, "profile_name", None),
                "description": getattr(obj, "description", None),
                "attributes": _safe_dict(getattr(obj, "attributes", None)),
            }
        )
    elif object_type == "agent":
        details.update(
            {
                "agent_name": getattr(obj, "agent_name", None),
                "description": getattr(obj, "description", None),
                "attributes": _safe_dict(getattr(obj, "attributes", None)),
            }
        )
    elif object_type == "tool":
        details.update(
            {
                "tool_name": getattr(obj, "tool_name", None),
                "description": getattr(obj, "description", None),
                "attributes": _safe_dict(getattr(obj, "attributes", None)),
            }
        )
    elif object_type == "task":
        details.update(
            {
                "task_name": getattr(obj, "task_name", None),
                "description": getattr(obj, "description", None),
                "attributes": _safe_dict(getattr(obj, "attributes", None)),
            }
        )
    elif object_type == "team":
        details.update(
            {
                "team_name": getattr(obj, "team_name", None),
                "description": getattr(obj, "description", None),
                "attributes": _safe_dict(getattr(obj, "attributes", None)),
            }
        )
    else:
        details["repr"] = str(obj)

    logger.info("OBJECT_DETAILS: %s", details)
    print("OBJECT_DETAILS:", details)


@pytest.fixture(scope="session")
def setup_test_user(test_env):
    try:
        select_ai.disconnect()
    except Exception:
        pass

    select_ai.connect(**test_env.connect_params(admin=True))
    try:
        try:
            select_ai.grant_privileges(users=[test_env.test_user])
        except Exception as exc:
            msg = str(exc)
            if (
                "ORA-01749" not in msg
                and "Cannot GRANT or REVOKE privileges to or from yourself" not in msg
            ):
                raise

        select_ai.grant_http_access(
            users=[test_env.test_user],
            provider_endpoint=select_ai.OpenAIProvider.provider_endpoint,
        )
    finally:
        select_ai.disconnect()
        select_ai.connect(**test_env.connect_params())


@pytest.fixture(scope="session")
def openai_cred():
    api_key = os.getenv("PYSAI_TEST_OPENAI_API_KEY")
    assert api_key, "PYSAI_TEST_OPENAI_API_KEY not set"

    select_ai.create_credential(
        credential={
            "credential_name": "OPENAI_CRED",
            "username": "openai",
            "password": api_key,
        },
        replace=True,
    )

    return "OPENAI_CRED"


@pytest.fixture(scope="session")
def email_cred():
    smtp_username = os.getenv("PYSAI_TEST_EMAIL_CRED_USERNAME")
    smtp_password = os.getenv("PYSAI_TEST_EMAIL_CRED_PASSWORD")

    assert smtp_username, "PYSAI_TEST_EMAIL_CRED_USERNAME not set"
    assert smtp_password, "PYSAI_TEST_EMAIL_CRED_PASSWORD not set"

    select_ai.create_credential(
        credential={
            "credential_name": "EMAIL_CRED",
            "username": smtp_username,
            "password": smtp_password,
        },
        replace=True,
    )

    return "EMAIL_CRED"


@pytest.fixture(scope="session")
def allow_network_acl():
    with select_ai.cursor() as cur:
        cur.execute("SELECT USER FROM dual")
        db_user = cur.fetchone()[0]

        def append_ace(host, privileges):
            try:
                cur.execute(
                    f"""
                    BEGIN
                        DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
                            host => '{host}',
                            ace  => xs$ace_type(
                                       privilege_list => xs$name_list({','.join([f"'{p}'" for p in privileges])}),
                                       principal_name => '{db_user}',
                                       principal_type => xs_acl.ptype_db
                                   )
                        );
                    END;
                    """
                )
            except Exception as exc:
                msg = str(exc)
                if (
                    "ORA-46212" in msg
                    or "ORA-46313" in msg
                    or "already exists" in msg
                ):
                    return
                raise

        append_ace(
            "smtp.email.us-ashburn-1.oci.oraclecloud.com",
            ["connect", "smtp"],
        )

        for host in ["api.openai.com", "a.co","amazon.in"]:
            append_ace(host, ["connect", "http"])

    yield


# ----------------------------------------------------------------------
# MAIN TEST
# ----------------------------------------------------------------------

def test_3800_agent_end_to_end(
    profile_attributes, setup_test_user, openai_cred, email_cred, allow_network_acl
):
    """
    End-to-end Select AI Agent integration test.
    
    """

    # -------------------------------
    # PROFILE
    # -------------------------------
    logger.info("Starting End-to-End Agent Test")

    # ---------------- PROFILE ----------------

    oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
    assert oci_compartment_id, "PYSAI_TEST_OCI_COMPARTMENT_ID not set"

    profile_attributes.provider.oci_compartment_id = oci_compartment_id

    profile = select_ai.Profile(
        profile_name="GEN1_PROFILE",
        attributes=profile_attributes,
        replace=True,
    )
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
                enable_human_tool=True,
            ),
        )
        agent.create(replace=True)
        log_object_details("create_agent", "agent", agent)

        assert agent.agent_name == "CustomerAgent"

    # -------------------------------
    # TOOLS
    # -------------------------------
    with log_step("Create tools"):

        # Human tool
        Tool.create_built_in_tool(
            tool_name="Human",
            description="Human intervention tool",
            tool_type="HUMAN",
            tool_params=ToolParams(),
            replace=True,
        )

        websearch_tool = Tool(
            tool_name="Websearch",
            attributes=ToolAttributes(
                tool_type="WEBSEARCH",
                instruction="Use this tool to find the current price of a product from a URL.",
                tool_params=ToolParams(
                    credential_name="OPENAI_CRED"
                ),
            ),
        )
        websearch_tool.create(replace=True)
        log_object_details("create_websearch_tool", "tool", websearch_tool)

        # Email notification tool
        email_recipient = os.getenv("PYSAI_TEST_EMAIL_RECIPIENT")
        email_sender = os.getenv("PYSAI_TEST_EMAIL_SENDER")
        assert email_recipient, "PYSAI_TEST_EMAIL_RECIPIENT not set"
        assert email_sender, "PYSAI_TEST_EMAIL_SENDER not set"
        email_tool = Tool(
            tool_name="Email",
            attributes=ToolAttributes(
                tool_type="NOTIFICATION",
                tool_params=ToolParams(
                    credential_name="EMAIL_CRED",
                    notification_type="EMAIL",
                    recipient=email_recipient,
                    sender=email_sender,
                    smtp_host="smtp.email.us-ashburn-1.oci.oraclecloud.com",
                ),
            ),
        )
        email_tool.create(replace=True)
        log_object_details("create_email_tool", "tool", email_tool)

        assert Tool("Human") is not None
        assert Tool("Email") is not None

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
                tools=["Human", "Websearch", "Email"],
            ),
        )
        task.create(replace=True)
        log_object_details("create_task", "task", task)

        assert task.task_name == "Return_And_Price_Match"
        assert set(task.attributes.tools) == {"Human", "Websearch", "Email"}

    assert task.task_name == "Return_And_Price_Match"
    # Corrected assert to match the 3 tools
    assert set(task.attributes.tools) == {"Human", "Websearch", "Email"}
    
    # -------------------------------
    # TEAM
    # -------------------------------
    with log_step("Create team"):
        team = Team(
            team_name="ReturnAgency",
            attributes=TeamAttributes(
                agents=[{
                    "name": "CustomerAgent",
                    "task": "Return_And_Price_Match",
                }],
                process="sequential",
            ),
        )
        team.create(enabled=True, replace=True)
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

            # ---- PRINT + LOG RESPONSE ----
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

        decoded_tool_history = []
        for row in tool_history:
            decoded_row = []
            for value in row:
                if hasattr(value, "read"):
                    decoded_row.append(value.read())
                else:
                    decoded_row.append(value)
            decoded_tool_history.append(tuple(decoded_row))

        print(decoded_tool_history)
        logger.info("Tool history rows fetched: %d", len(decoded_tool_history))
        for row in decoded_tool_history:
            logger.info("TOOL_HISTORY_ROW: %s", row)

        assert decoded_tool_history
