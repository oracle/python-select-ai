# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1700 - AsyncProfile generate API tests
"""

import json
import logging
import uuid

import oracledb
import pandas as pd
import pytest
import select_ai
from select_ai import (
    AsyncConversation,
    AsyncProfile,
    ConversationAttributes,
    ProfileAttributes,
)
from select_ai.profile import Action

logger = logging.getLogger(__name__)

PROFILE_PREFIX = f"PYSAI_1700_{uuid.uuid4().hex.upper()}"

PROMPTS = [
    "What is a database?",
    "How many gymnasts in database?",
    "How many people are in the database?",
]


@pytest.fixture(scope="module")
def async_generate_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
def async_generate_profile_attributes(
    oci_credential, async_generate_provider, test_env
):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[
            {"owner": test_env.test_user, "name": "people"},
            {"owner": test_env.test_user, "name": "gymnast"},
        ],
        provider=async_generate_provider,
    )


@pytest.fixture(scope="module")
async def async_generate_profile(async_generate_profile_attributes):
    logger.info(
        "Creating async generate profile %s", f"{PROFILE_PREFIX}_POSITIVE"
    )
    profile = await AsyncProfile(
        profile_name=f"{PROFILE_PREFIX}_POSITIVE",
        attributes=async_generate_profile_attributes,
        description="Async generate calls test profile",
        replace=True,
    )
    await profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    logger.info("Deleting async generate profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture
async def async_negative_profile(
    oci_credential, async_generate_provider, test_env
):
    logger.info("Creating async negative generate profile")
    profile_name = f"{PROFILE_PREFIX}_NEG_{uuid.uuid4().hex.upper()}"
    attributes = ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=async_generate_provider,
    )
    profile = await AsyncProfile(
        profile_name=profile_name,
        attributes=attributes,
        description="Async generate calls negative test profile",
        replace=True,
    )
    await profile.set_attribute(
        attribute_name="object_list",
        attribute_value=json.dumps(
            [
                {"owner": test_env.test_user, "name": "people"},
                {"owner": test_env.test_user, "name": "gymnast"},
            ]
        ),
    )
    await profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    logger.info(
        "Deleting async negative generate profile %s", profile.profile_name
    )
    await profile.delete(force=True)


@pytest.mark.anyio
async def test_1700_action_enum_members():
    """Validate Action enum exposes expected members"""
    logger.info("Validating async Action enum exposes expected members")
    for member in [
        "RUNSQL",
        "SHOWSQL",
        "EXPLAINSQL",
        "NARRATE",
        "CHAT",
        "SHOWPROMPT",
    ]:
        assert hasattr(Action, member)


@pytest.mark.anyio
async def test_1701_action_enum_values():
    """Validate Action enum values"""
    logger.info("Validating async Action enum values")
    assert Action.RUNSQL.value == "runsql"
    assert Action.SHOWSQL.value == "showsql"
    assert Action.EXPLAINSQL.value == "explainsql"
    assert Action.NARRATE.value == "narrate"
    assert Action.CHAT.value == "chat"


@pytest.mark.anyio
async def test_1702_action_from_string():
    """Validate Action enum construction from string"""
    logger.info("Validating async Action enum from string conversions")
    assert Action("runsql") is Action.RUNSQL
    assert Action("chat") is Action.CHAT
    assert Action("explainsql") is Action.EXPLAINSQL
    assert Action("narrate") is Action.NARRATE
    assert Action("showsql") is Action.SHOWSQL


@pytest.mark.anyio
async def test_1703_action_invalid_string():
    """Invalid enum string raises ValueError"""
    logger.info("Validating async invalid Action string raises ValueError")
    with pytest.raises(ValueError):
        Action("invalid_action")


@pytest.mark.anyio
async def test_1704_show_sql(async_generate_profile):
    """show_sql returns SQL text"""
    logger.info("Validating async show_sql returns SQL text")
    for prompt in PROMPTS[1:]:
        show_sql = await async_generate_profile.show_sql(prompt=prompt)
        logger.debug("Response = %s", show_sql)
        assert isinstance(show_sql, str)
        assert "SELECT" in show_sql.upper()


@pytest.mark.anyio
async def test_1705_show_prompt(async_generate_profile):
    """show_prompt returns prompt text"""
    logger.info("Validating async show_prompt returns text")
    for prompt in PROMPTS:
        show_prompt = await async_generate_profile.show_prompt(prompt=prompt)
        logger.debug("Response = %s", show_prompt)
        assert isinstance(show_prompt, str)
        assert len(show_prompt) > 0
        assert '"type" : "TEXT"' in show_prompt


@pytest.mark.anyio
async def test_1706_run_sql(async_generate_profile):
    """run_sql returns DataFrame"""
    logger.info("Validating async run_sql returns DataFrame")
    dataframe = await async_generate_profile.run_sql(prompt=PROMPTS[1])
    logger.debug("Response = %s", dataframe)
    assert isinstance(dataframe, pd.DataFrame)
    assert len(dataframe.columns) > 0


@pytest.mark.anyio
async def test_1707_chat(async_generate_profile):
    """chat returns text response"""
    logger.info("Validating async chat returns text response")
    response = await async_generate_profile.chat(prompt="What is OCI ?")
    logger.debug("Response = %s", response)
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Oracle Cloud Infrastructure" in response


@pytest.mark.anyio
async def test_1708_narrate(async_generate_profile):
    """narrate returns narrative text"""
    logger.info("Validating async narrate returns narrative text")
    for prompt in PROMPTS[1:0]:
        narration = await async_generate_profile.narrate(prompt=prompt)
        logger.info("Response = %s", narration)
        assert isinstance(narration, str)
        assert len(narration) > 0
        assert "in the database" in narration


@pytest.mark.anyio
async def test_1709_chat_session(async_generate_profile):
    """chat_session provides a session context"""
    logger.info("Validating async chat_session context manager")
    conversation = AsyncConversation(attributes=ConversationAttributes())
    async with async_generate_profile.chat_session(
        conversation=conversation, delete=True
    ) as session:
        assert session is not None


@pytest.mark.anyio
async def test_1710_explain_sql(async_generate_profile):
    """explain_sql returns explanation text"""
    logger.info("Validating async explain_sql returns explanation text")
    for prompt in PROMPTS:
        explain_sql = await async_generate_profile.explain_sql(prompt=prompt)
        logger.debug("Response = %s", explain_sql)
        assert isinstance(explain_sql, str)
        assert len(explain_sql) > 0


@pytest.mark.anyio
async def test_1711_generate_runsql(async_generate_profile):
    """generate with RUNSQL returns DataFrame"""
    logger.info("Validating async generate with RUNSQL returns DataFrame")
    dataframe = await async_generate_profile.generate(
        prompt=PROMPTS[1], action=Action.RUNSQL
    )
    logger.debug("Response = %s", dataframe)
    assert isinstance(dataframe, pd.DataFrame)


@pytest.mark.anyio
async def test_1712_generate_showsql(async_generate_profile):
    """generate with SHOWSQL returns SQL"""
    logger.info("Validating async generate with SHOWSQL returns SQL")
    sql = await async_generate_profile.generate(
        prompt=PROMPTS[1], action=Action.SHOWSQL
    )
    logger.debug("Response = %s", sql)
    assert isinstance(sql, str)
    assert "SELECT" in sql.upper()


@pytest.mark.anyio
async def test_1713_generate_chat(async_generate_profile):
    """generate with CHAT returns response"""
    logger.info("Validating async generate with CHAT returns response")
    chat_response = await async_generate_profile.generate(
        prompt="Tell me about OCI", action=Action.CHAT
    )
    logger.debug("Response = %s", chat_response)
    assert isinstance(chat_response, str)
    assert len(chat_response) > 0
    assert "Oracle Cloud Infrastructure" in chat_response


@pytest.mark.anyio
async def test_1714_generate_narrate(async_generate_profile):
    """generate with NARRATE returns response"""
    logger.info("Validating async generate with NARRATE returns response")
    narrate_response = await async_generate_profile.generate(
        prompt=PROMPTS[1], action=Action.NARRATE
    )
    logger.debug("Response = %s", narrate_response)
    assert isinstance(narrate_response, str)
    assert len(narrate_response) > 0
    assert "in the database" in narrate_response


@pytest.mark.anyio
async def test_1715_generate_explainsql(async_generate_profile):
    """generate with EXPLAINSQL returns explanation"""
    logger.info(
        "Validating async generate with EXPLAINSQL returns explanation"
    )
    for prompt in PROMPTS:
        explain_sql = await async_generate_profile.generate(
            prompt=prompt, action=Action.EXPLAINSQL
        )
        logger.debug("Response = %s", explain_sql)
        assert isinstance(explain_sql, str)
        assert len(explain_sql) > 0


@pytest.mark.anyio
async def test_1716_empty_prompt_raises_value_error(async_negative_profile):
    """Empty prompts raise ValueError for async profile methods"""
    logger.info("Validating async empty prompts raise ValueError")
    with pytest.raises(ValueError):
        await async_negative_profile.chat(prompt="")
    with pytest.raises(ValueError):
        await async_negative_profile.narrate(prompt="")
    with pytest.raises(ValueError):
        await async_negative_profile.show_sql(prompt="")
    with pytest.raises(ValueError):
        await async_negative_profile.show_prompt(prompt="")
    with pytest.raises(ValueError):
        await async_negative_profile.run_sql(prompt="")
    with pytest.raises(ValueError):
        await async_negative_profile.explain_sql(prompt="")


@pytest.mark.anyio
async def test_1717_none_prompt_raises_value_error(async_negative_profile):
    """None prompts raise ValueError for async profile methods"""
    logger.info("Validating async None prompts raise ValueError")
    with pytest.raises(ValueError):
        await async_negative_profile.chat(prompt=None)
    with pytest.raises(ValueError):
        await async_negative_profile.narrate(prompt=None)
    with pytest.raises(ValueError):
        await async_negative_profile.show_sql(prompt=None)
    with pytest.raises(ValueError):
        await async_negative_profile.show_prompt(prompt=None)
    with pytest.raises(ValueError):
        await async_negative_profile.run_sql(prompt=None)
    with pytest.raises(ValueError):
        await async_negative_profile.explain_sql(prompt=None)


# @pytest.mark.anyio
# async def test_1718_run_sql_with_ambiguous_prompt(async_negative_profile):
#     """Ambiguous prompt raises DatabaseError for run_sql"""
#     with pytest.raises(oracledb.DatabaseError):
#         await async_negative_profile.run_sql(prompt="select from user")


# @pytest.mark.anyio
# async def test_1719_run_sql_with_invalid_object_list(async_negative_profile, test_env):
#     """run_sql with non existent table raises DatabaseError"""
#     await async_negative_profile.set_attribute(
#         attribute_name="object_list",
#         attribute_value=json.dumps(
#             [{"owner": test_env.test_user, "name": "non_existent_table"}]
#         ),
#     )
#     with pytest.raises(oracledb.DatabaseError):
#         await async_negative_profile.run_sql(prompt="How many entries in the table")
