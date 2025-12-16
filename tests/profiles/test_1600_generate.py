# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1600 - Profile generate API tests
"""

import uuid

import oracledb
import pandas as pd
import pytest
import select_ai
from select_ai import Conversation, ConversationAttributes, Profile, ProfileAttributes
from select_ai.profile import Action


PROFILE_PREFIX = f"PYSAI_1600_{uuid.uuid4().hex.upper()}"

PROMPTS = [
    "What is a database?",
    "How many gymnasts in database?",
    "How many people are there in the database?",
]


@pytest.fixture(scope="module")
def generate_provider(oci_compartment_id):
    return select_ai.OCIGenAIProvider(
        oci_compartment_id=oci_compartment_id,
        oci_apiformat="GENERIC",
    )


@pytest.fixture(scope="module")
def generate_profile_attributes(oci_credential, generate_provider):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[
            {"owner": "ADMIN", "name": "people"},
            {"owner": "ADMIN", "name": "gymnast"},
        ],
        provider=generate_provider,
    )


@pytest.fixture(scope="module")
def generate_profile(generate_profile_attributes):
    profile = Profile(
        profile_name=f"{PROFILE_PREFIX}_POSITIVE",
        attributes=generate_profile_attributes,
        description="Generate Calls Test Profile",
        replace=True,
    )
    profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    try:
        profile.delete(force=True)
    except Exception:
        pass


@pytest.fixture
def negative_profile(oci_credential, generate_provider):
    profile_name = f"{PROFILE_PREFIX}_NEG_{uuid.uuid4().hex.upper()}"
    attributes = ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=generate_provider,
    )
    profile = Profile(
        profile_name=profile_name,
        attributes=attributes,
        description="Generate Calls Negative Test Profile",
        replace=True,
    )
    profile.set_attribute(
        attribute_name="object_list",
        attribute_value='[{"owner": "ADMIN", "name": "people"},'
        '{"owner": "ADMIN", "name": "gymnast"}]',
    )
    profile.set_attribute(
        attribute_name="model",
        attribute_value="meta.llama-3.1-405b-instruct",
    )
    yield profile
    try:
        profile.delete(force=True)
    except Exception:
        pass


def test_1600_action_enum_members():
    """Validate Action enum exposes expected members"""
    for member in ["RUNSQL", "SHOWSQL", "EXPLAINSQL", "NARRATE", "CHAT", "SHOWPROMPT"]:
        assert hasattr(Action, member)


def test_1601_action_enum_values():
    """Validate Action enum values"""
    assert Action.RUNSQL.value == "runsql"
    assert Action.SHOWSQL.value == "showsql"
    assert Action.EXPLAINSQL.value == "explainsql"
    assert Action.NARRATE.value == "narrate"
    assert Action.CHAT.value == "chat"


def test_1602_action_from_string():
    """Validate Action enum construction from string"""
    assert Action("runsql") is Action.RUNSQL
    assert Action("chat") is Action.CHAT
    assert Action("explainsql") is Action.EXPLAINSQL
    assert Action("narrate") is Action.NARRATE
    assert Action("showsql") is Action.SHOWSQL


def test_1603_action_invalid_string():
    """Invalid enum string raises ValueError"""
    with pytest.raises(ValueError):
        Action("invalid_action")


def test_1604_show_sql(generate_profile):
    """show_sql returns SQL text"""
    for prompt in PROMPTS:
        show_sql = generate_profile.show_sql(prompt=prompt)
        assert isinstance(show_sql, str)
        assert "SELECT" in show_sql.upper()


def test_1605_show_prompt(generate_profile):
    """show_prompt returns prompt text"""
    for prompt in PROMPTS:
        show_prompt = generate_profile.show_prompt(prompt=prompt)
        assert isinstance(show_prompt, str)
        assert len(show_prompt) > 0


def test_1606_run_sql(generate_profile):
    """run_sql returns DataFrame"""
    df = generate_profile.run_sql(prompt=PROMPTS[1])
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) > 0


def test_1607_chat(generate_profile):
    """chat returns text response"""
    response = generate_profile.chat(prompt="What is OCI ?")
    assert isinstance(response, str)
    assert len(response) > 0


def test_1608_narrate(generate_profile):
    """narrate returns narrative text"""
    for prompt in PROMPTS:
        narration = generate_profile.narrate(prompt=prompt)
        assert isinstance(narration, str)
        assert len(narration) > 0


def test_1609_chat_session(generate_profile):
    """chat_session provides a session context"""
    conversation = Conversation(attributes=ConversationAttributes())
    with generate_profile.chat_session(conversation=conversation, delete=True) as session:
        assert session is not None


def test_1610_explain_sql(generate_profile):
    """explain_sql returns explanation text"""
    for prompt in PROMPTS:
        explain_sql = generate_profile.explain_sql(prompt=prompt)
        assert isinstance(explain_sql, str)
        assert len(explain_sql) > 0


def test_1611_generate_runsql(generate_profile):
    """generate with RUNSQL returns DataFrame"""
    df = generate_profile.generate(prompt=PROMPTS[1], action=Action.RUNSQL)
    assert isinstance(df, pd.DataFrame)


def test_1612_generate_showsql(generate_profile):
    """generate with SHOWSQL returns SQL"""
    sql = generate_profile.generate(prompt=PROMPTS[1], action=Action.SHOWSQL)
    assert isinstance(sql, str)
    assert "SELECT" in sql.upper()


def test_1613_generate_chat(generate_profile):
    """generate with CHAT returns response"""
    chat_resp = generate_profile.generate(prompt="Tell me about OCI", action=Action.CHAT)
    assert isinstance(chat_resp, str)
    assert len(chat_resp) > 0


def test_1614_generate_narrate(generate_profile):
    """generate with NARRATE returns response"""
    narrate_resp = generate_profile.generate(prompt=PROMPTS[1], action=Action.NARRATE)
    assert isinstance(narrate_resp, str)
    assert len(narrate_resp) > 0


def test_1615_generate_explainsql(generate_profile):
    """generate with EXPLAINSQL returns explanation"""
    for prompt in PROMPTS:
        explain_sql = generate_profile.generate(prompt=prompt, action=Action.EXPLAINSQL)
        assert isinstance(explain_sql, str)
        assert len(explain_sql) > 0


def test_1616_empty_prompt_raises_value_error(negative_profile):
    """Empty prompts raise ValueError for profile methods"""
    with pytest.raises(ValueError):
        negative_profile.chat(prompt="")
    with pytest.raises(ValueError):
        negative_profile.narrate(prompt="")
    with pytest.raises(ValueError):
        negative_profile.show_sql(prompt="")
    with pytest.raises(ValueError):
        negative_profile.show_prompt(prompt="")
    with pytest.raises(ValueError):
        negative_profile.run_sql(prompt="")
    with pytest.raises(ValueError):
        negative_profile.explain_sql(prompt="")


def test_1617_none_prompt_raises_value_error(negative_profile):
    """None prompts raise ValueError for profile methods"""
    with pytest.raises(ValueError):
        negative_profile.chat(prompt=None)
    with pytest.raises(ValueError):
        negative_profile.narrate(prompt=None)
    with pytest.raises(ValueError):
        negative_profile.show_sql(prompt=None)
    with pytest.raises(ValueError):
        negative_profile.show_prompt(prompt=None)
    with pytest.raises(ValueError):
        negative_profile.run_sql(prompt=None)
    with pytest.raises(ValueError):
        negative_profile.explain_sql(prompt=None)


def test_1618_run_sql_with_ambiguous_prompt(negative_profile):
    """Ambiguous prompt raises DatabaseError for run_sql"""
    with pytest.raises(oracledb.DatabaseError):
        negative_profile.run_sql(prompt="select from user")


def test_1619_run_sql_with_invalid_object_list(negative_profile):
    """run_sql with non existent table raises DatabaseError"""
    negative_profile.set_attribute(
        attribute_name="object_list",
        attribute_value='[{"owner": "ADMIN", "name": "non_existent_table"}]',
    )
    with pytest.raises(oracledb.DatabaseError):
        negative_profile.run_sql(prompt="How many entries in the table")

