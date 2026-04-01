# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import datetime
import json

import pytest

import select_ai.base_profile as base_profile
from select_ai.action import Action
from select_ai.base_profile import (
    BaseProfile,
    ProfileAttributes,
    convert_json_rows_to_df,
    no_data_for_prompt,
    validate_params_for_feedback,
    validate_params_for_summary,
)
from select_ai.feedback import FeedbackOperation, FeedbackType
from select_ai.provider import OpenAIProvider
from select_ai.summary import SummaryParams

pytestmark = pytest.mark.unit


def test_4500_profile_attributes_reject_invalid_provider_type():
    with pytest.raises(ValueError):
        ProfileAttributes(provider="invalid")


def test_4501_profile_attributes_json_flattens_provider_fields():
    attributes = ProfileAttributes(
        credential_name="cred",
        provider=OpenAIProvider(model="gpt-4o-mini"),
    )
    payload = json.loads(attributes.json())
    assert payload["credential_name"] == "cred"
    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-4o-mini"


def test_4502_profile_attributes_create_builds_provider_subclass():
    attributes = ProfileAttributes.create(
        provider="openai",
        model="gpt-4o-mini",
        credential_name="cred",
    )
    assert isinstance(attributes.provider, OpenAIProvider)
    assert attributes.provider.model == "gpt-4o-mini"


@pytest.mark.anyio
async def test_4503_profile_attributes_async_create_reads_async_lob(
    monkeypatch, fake_async_lob
):
    monkeypatch.setattr(base_profile.oracledb, "AsyncLOB", type(fake_async_lob))
    attributes = await ProfileAttributes.async_create(
        provider="openai",
        model=fake_async_lob,
        credential_name="cred",
    )
    assert attributes.provider.model == fake_async_lob.value


def test_4504_profile_attributes_create_reads_lob(monkeypatch, fake_lob):
    monkeypatch.setattr(base_profile.oracledb, "LOB", type(fake_lob))
    attributes = ProfileAttributes.create(
        provider="openai",
        model=fake_lob,
        credential_name="cred",
    )
    assert attributes.provider.model == fake_lob.value


def test_4505_set_attribute_updates_provider_and_profile_fields():
    attributes = ProfileAttributes(
        provider=OpenAIProvider(model="gpt-4o-mini"),
        temperature=0.1,
    )
    attributes.set_attribute("model", "gpt-4.1-mini")
    attributes.set_attribute("temperature", 0.4)
    assert attributes.provider.model == "gpt-4.1-mini"
    assert attributes.temperature == 0.4


def test_4506_raise_error_if_profile_exists_requires_replace_or_merge():
    profile = BaseProfile(
        profile_name="demo",
        attributes=ProfileAttributes(provider=OpenAIProvider()),
    )
    with pytest.raises(base_profile.ProfileExistsError):
        profile._raise_error_if_profile_exists()


def test_4507_merge_attributes_prefers_saved_values_when_missing():
    profile = BaseProfile(profile_name="demo")
    saved_attributes = ProfileAttributes(
        provider=OpenAIProvider(model="gpt-4o-mini"),
        temperature=0.2,
    )
    profile._merge_attributes(saved_attributes, "saved description")
    assert profile.attributes == saved_attributes
    assert profile.description == "saved description"


def test_4508_merge_attributes_merges_non_null_values_when_merge_enabled():
    profile = BaseProfile(
        profile_name="demo",
        attributes=ProfileAttributes(temperature=0.9),
        merge=True,
    )
    saved_attributes = ProfileAttributes(
        provider=OpenAIProvider(model="gpt-4o-mini"),
        temperature=0.2,
    )
    profile._merge_attributes(saved_attributes, "saved description")
    assert profile.replace is True
    assert profile.attributes.temperature == 0.9
    assert profile.attributes.provider.model == "gpt-4o-mini"


def test_4509_no_data_for_prompt_handles_empty_responses():
    assert no_data_for_prompt(None) is True
    assert no_data_for_prompt("No data found for the prompt.") is True
    assert no_data_for_prompt("result") is False


def test_4510_validate_params_for_feedback_builds_prompt_payload():
    params = validate_params_for_feedback(
        feedback_type=FeedbackType.NEGATIVE,
        feedback_content="bad ordering",
        prompt_spec=("show all people", Action.SHOWSQL),
        response="SELECT * FROM people",
    )
    assert params["feedback_type"] == "negative"
    assert params["operation"] == "add"
    assert params["sql_text"] == "select ai showsql show all people"


def test_4511_validate_params_for_feedback_requires_response_for_negative_add():
    with pytest.raises(AttributeError):
        validate_params_for_feedback(
            feedback_type=FeedbackType.NEGATIVE,
            feedback_content="bad ordering",
            prompt_spec=("show all people", Action.SHOWSQL),
        )


def test_4512_validate_params_for_feedback_rejects_invalid_action():
    with pytest.raises(AttributeError):
        validate_params_for_feedback(
            feedback_type=FeedbackType.POSITIVE,
            feedback_content="good",
            prompt_spec=("show all people", Action.CHAT),
        )


def test_4513_validate_params_for_feedback_accepts_sql_id_only():
    params = validate_params_for_feedback(
        feedback_type=FeedbackType.POSITIVE,
        feedback_content="great",
        sql_id="abc123",
        operation=FeedbackOperation.DELETE,
    )
    assert params == {
        "operation": "delete",
        "feedback_content": "great",
        "feedback_type": "positive",
        "sql_id": "abc123",
    }


def test_4514_validate_params_for_summary_accepts_content_or_location():
    params = validate_params_for_summary(
        prompt="Summarize",
        content="demo content",
        params=SummaryParams(min_words=10),
    )
    assert params["content"] == "demo content"
    assert json.loads(params["parameters"]) == {"min_words": 10}


def test_4515_validate_params_for_summary_rejects_invalid_source_combinations():
    with pytest.raises(AttributeError):
        validate_params_for_summary()
    with pytest.raises(AttributeError):
        validate_params_for_summary(content="x", location_uri="y")


def test_4516_convert_json_rows_to_df_handles_valid_and_invalid_payloads():
    frame = convert_json_rows_to_df('[{"name": "Alice"}]')
    assert list(frame.columns) == ["name"]
    with pytest.raises(base_profile.InvalidSQLError):
        convert_json_rows_to_df("not-json")

