# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0
# -----------------------------------------------------------------------------

"""
3800 - Async end-to-end Select AI Agent integration test
"""

import logging
import os
import time
import uuid
from contextlib import contextmanager

import pytest
import select_ai
from select_ai.agent import (
    AgentAttributes,
    AsyncAgent,
    AsyncTask,
    AsyncTeam,
    AsyncTool,
    TaskAttributes,
    TeamAttributes,
    ToolAttributes,
    ToolParams,
)

pytestmark = pytest.mark.anyio

# ----------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_test_3800_async_agente2e.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

root = logging.getLogger()
root.setLevel(logging.INFO)
for h in root.handlers[:]:
    root.removeHandler(h)

fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)

logger = logging.getLogger(__name__)


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


@pytest.fixture(scope="module", autouse=True)
async def async_connect(test_env):
    logger.info("Opening async database connection")
    await select_ai.async_connect(**test_env.connect_params())
    yield
    logger.info("Closing async database connection")
    await select_ai.async_disconnect()


async def test_agent_end_to_end_async(profile_attributes):
    """End-to-end Select AI Agent integration test (async)."""

    run_id = uuid.uuid4().hex.upper()

    profile_name = f"GEN1_PROFILE_{run_id}"
    agent_name = f"CustomerAgent_{run_id}"
    human_tool_name = f"Human_{run_id}"
    websearch_tool_name = f"Websearch_{run_id}"
    email_tool_name = f"Email_{run_id}"
    task_name = f"Return_And_Price_Match_{run_id}"
    team_name = f"ReturnAgency_{run_id}"

    created = {
        "team": None,
        "task": None,
        "tools": [],
        "agent": None,
        "profile": None,
    }

    logger.info("Starting async End-to-End Agent Test")
    logger.info(
        "Run identifiers | profile=%s agent=%s task=%s team=%s",
        profile_name,
        agent_name,
        task_name,
        team_name,
    )

    oci_compartment_id = os.getenv("PYSAI_TEST_OCI_COMPARTMENT_ID")
    assert oci_compartment_id, "PYSAI_TEST_OCI_COMPARTMENT_ID not set"

    profile_attributes.provider.oci_compartment_id = oci_compartment_id

    try:
        with log_step("Create profile"):
            profile = await select_ai.AsyncProfile(
                profile_name=profile_name,
                attributes=profile_attributes,
                replace=True,
            )
            created["profile"] = profile
            logger.info("Created profile: %s", profile.profile_name)
            log_object_details("create_profile", "profile", profile)

        with log_step("Create agent"):
            agent = AsyncAgent(
                agent_name=agent_name,
                attributes=AgentAttributes(
                    profile_name=profile_name,
                    role=(
                        "You are an experienced customer agent handling returns."
                    ),
                    enable_human_tool=True,
                ),
            )
            await agent.create(replace=True)
            created["agent"] = agent
            logger.info("Created agent: %s", agent.agent_name)
            log_object_details("create_agent", "agent", agent)
            assert agent.agent_name == agent_name

        with log_step("Create tools"):
            human_tool = await AsyncTool.create_built_in_tool(
                tool_name=human_tool_name,
                description="Human intervention tool",
                tool_type=select_ai.agent.ToolType.HUMAN,
                tool_params=ToolParams(),
                replace=True,
            )
            created["tools"].append(human_tool)

            websearch_tool = AsyncTool(
                tool_name=websearch_tool_name,
                attributes=ToolAttributes(
                    tool_type=select_ai.agent.ToolType.WEBSEARCH,
                    instruction=(
                        "Use this tool to find current product price from a URL."
                    ),
                    tool_params=ToolParams(credential_name="OPENAI_CRED"),
                ),
            )
            await websearch_tool.create(replace=True)
            created["tools"].append(websearch_tool)
            log_object_details("create_websearch_tool", "tool", websearch_tool)

            email_tool = AsyncTool(
                tool_name=email_tool_name,
                attributes=ToolAttributes(
                    tool_type=select_ai.agent.ToolType.NOTIFICATION,
                    tool_params=ToolParams(
                        credential_name="EMAIL_CRED",
                        notification_type="EMAIL",
                        recipient=os.getenv("PYSAI_TEST_EMAIL_RECIPIENT"),
                        sender=os.getenv("PYSAI_TEST_EMAIL_SENDER"),
                        smtp_host=os.getenv("PYSAI_TEST_EMAIL_SMTPHOST"),
                    ),
                ),
            )
            await email_tool.create(replace=True)
            created["tools"].append(email_tool)
            log_object_details("create_email_tool", "tool", email_tool)

            logger.info(
                "Created tools: %s",
                [t.tool_name for t in created["tools"]],
            )
            log_object_details("create_human_tool", "tool", human_tool)
            assert len(created["tools"]) == 3

        with log_step("Create task"):
            task = AsyncTask(
                task_name=task_name,
                attributes=TaskAttributes(
                    instruction=(
                        "Process a product return request from a customer. "
                        "1. Ask customer reason for return (price match or defective). "
                        "2. If price match: request link, use websearch, ask refund amount, "
                        "send email only if accepted. "
                        "3. If defective: process defective return."
                    ),
                    tools=[human_tool_name, websearch_tool_name, email_tool_name],
                ),
            )
            await task.create(replace=True)
            created["task"] = task

            logger.info("Created task: %s", task.task_name)
            log_object_details("create_task", "task", task)
            assert task.task_name == task_name
            assert set(task.attributes.tools) == {
                human_tool_name,
                websearch_tool_name,
                email_tool_name,
            }

        with log_step("Create team"):
            team = AsyncTeam(
                team_name=team_name,
                attributes=TeamAttributes(
                    agents=[
                        {
                            "name": agent_name,
                            "task": task_name,
                        }
                    ],
                    process="sequential",
                ),
            )
            await team.create(enabled=True, replace=True)
            created["team"] = team

            logger.info("Created team: %s", team.team_name)
            log_object_details("create_team", "team", team)
            assert team.team_name == team_name

        with log_step("Run async agent conversation"):
            conversation_id = str(uuid.uuid4())
            prompts = [
                "I want to return an office chair",
                "The price when I bought it is 100. I found a cheaper price",
                "Price match link https://www.ikea.com/us/en/p/stefan-chair-brown-black-00211088/",
                "Yes, I would like to proceed with a refund",
                "If you have not started the refund, please do",
            ]

            for idx, prompt in enumerate(prompts, start=1):
                logger.info("USER %d: %s", idx, prompt)
                response = await team.run(
                    prompt=prompt,
                    params={"conversation_id": conversation_id},
                )

                print(f"\nASYNC AGENT RESPONSE {idx}:\n{response}\n")
                logger.info("ASYNC AGENT RESPONSE %d: %s", idx, response)

                assert response is not None
                assert isinstance(response, str)
                assert len(response.strip()) > 0

    finally:
        with log_step("Cleanup async e2e objects"):
            if created["team"] is not None:
                logger.info("Deleting team: %s", created["team"].team_name)
                await created["team"].delete(force=True)

            if created["task"] is not None:
                logger.info("Deleting task: %s", created["task"].task_name)
                await created["task"].delete(force=True)

            for tool in reversed(created["tools"]):
                logger.info("Deleting tool: %s", tool.tool_name)
                await tool.delete(force=True)

            if created["agent"] is not None:
                logger.info("Deleting agent: %s", created["agent"].agent_name)
                await created["agent"].delete(force=True)

            if created["profile"] is not None:
                logger.info("Deleting profile: %s", created["profile"].profile_name)
                await created["profile"].delete(force=True)
