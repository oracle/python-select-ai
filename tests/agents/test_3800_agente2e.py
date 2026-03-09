# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0
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


# ----------------------------------------------------------------------
# MAIN TEST
# ----------------------------------------------------------------------

def test_agent_end_to_end(profile_attributes):
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

    select_ai.Profile(
        profile_name="GEN1_PROFILE",
        attributes=profile_attributes,
        replace=True,
    )

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

        # Email notification tool
        email_tool = Tool(
            tool_name="Email",
            attributes=ToolAttributes(
                tool_type="NOTIFICATION",
                tool_params=ToolParams(
                    credential_name="EMAIL_CRED",
                    notification_type="EMAIL",
                    recipient=os.getenv("PYSAI_TEST_EMAIL_RECIPIENT"),
                    sender=os.getenv("PYSAI_TEST_EMAIL_SENDER"),
                    smtp_host=os.getenv("PYSAI_TEST_EMAIL_SMTPHOST"),
                ),
            ),
        )
        email_tool.create(replace=True)

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

        assert team.team_name == "ReturnAgency"

    # -------------------------------
    # RUN CONVERSATION
    # -------------------------------
    with log_step("Run agent conversation"):
        conversation_id = str(uuid.uuid4())

        prompts = [
            "I want to return an office chair",
            "The price when I bought it is 100. But I found a cheaper price",
            "Here is the price match link https://www.ikea.com/us/en/p/stefan-chair-brown-black-00211088/",
            "Yes, I would like to proceed with a refund",
            "If you havent started the refund, please do"
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
