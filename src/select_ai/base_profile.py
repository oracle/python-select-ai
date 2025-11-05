# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from abc import ABC
from dataclasses import dataclass
from typing import List, Mapping, Optional, Tuple

import oracledb

from select_ai._abc import SelectAIDataClass
from select_ai.action import Action
from select_ai.feedback import (
    FeedbackOperation,
    FeedbackType,
)
from select_ai.provider import Provider
from select_ai.summary import SummaryParams


@dataclass
class ProfileAttributes(SelectAIDataClass):
    """
    Use this class to define attributes to manage and configure the behavior of
    an AI profile

    :param bool comments: True to include column comments in the metadata used
     for generating SQL queries from natural language prompts.
    :param bool constraints: True to include referential integrity constraints
     such as primary and foreign keys in the metadata sent to the LLM.
    :param bool conversation: Indicates if conversation history is enabled for
     a profile.
    :param str credential_name: The name of the credential to access the AI
     provider APIs.
    :param bool enforce_object_list: Specifies whether to restrict the LLM
     to generate SQL that uses only tables covered by the object list.
    :param int max_tokens: Denotes the number of tokens to return per
     generation. Default is 1024.
    :param List[Mapping] object_list: Array of JSON objects specifying
     the owner and object names that are eligible for natural language
     translation to SQL.
    :param str object_list_mode: Specifies whether to send metadata for the
     most relevant tables or all tables to the LLM. Supported values are -
     'automated' and 'all'
    :param select_ai.Provider provider: AI Provider
    :param str stop_tokens: The generated text will be terminated at the
     beginning of the earliest stop sequence. Sequence will be incorporated
     into the text. The attribute value must be a valid array of string values
     in JSON format
    :param float temperature: Temperature is a non-negative float number used
     to tune the degree of randomness. Lower temperatures mean less random
     generations.
    :param str vector_index_name: Name of the vector index

    """

    annotations: Optional[str] = None
    case_sensitive_values: Optional[bool] = None
    comments: Optional[bool] = None
    constraints: Optional[str] = None
    conversation: Optional[bool] = None
    credential_name: Optional[str] = None
    enable_custom_source_uri: Optional[bool] = None
    enable_sources: Optional[bool] = None
    enable_source_offsets: Optional[bool] = None
    enforce_object_list: Optional[bool] = None
    max_tokens: Optional[int] = 1024
    object_list: Optional[List[Mapping]] = None
    object_list_mode: Optional[str] = None
    provider: Optional[Provider] = None
    seed: Optional[str] = None
    stop_tokens: Optional[str] = None
    streaming: Optional[str] = None
    temperature: Optional[float] = None
    vector_index_name: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.provider and not isinstance(self.provider, Provider):
            raise ValueError(
                f"'provider' must be an object of " f"type select_ai.Provider"
            )

    def json(self, exclude_null=True):
        attributes = {}
        for k, v in self.dict(exclude_null=exclude_null).items():
            if isinstance(v, Provider):
                for provider_k, provider_v in v.dict(
                    exclude_null=exclude_null
                ).items():
                    attributes[Provider.key_alias(provider_k)] = provider_v
            else:
                attributes[k] = v
        return json.dumps(attributes)

    @classmethod
    def create(cls, **kwargs):
        provider_attributes = {}
        profile_attributes = {}
        for k, v in kwargs.items():
            if isinstance(v, oracledb.LOB):
                v = v.read()
            if k in Provider.keys():
                provider_attributes[Provider.key_alias(k)] = v
            else:
                profile_attributes[k] = v
        provider = Provider.create(**provider_attributes)
        profile_attributes["provider"] = provider
        return ProfileAttributes(**profile_attributes)

    @classmethod
    async def async_create(cls, **kwargs):
        provider_attributes = {}
        profile_attributes = {}
        for k, v in kwargs.items():
            if isinstance(v, oracledb.AsyncLOB):
                v = await v.read()
            if k in Provider.keys():
                provider_attributes[Provider.key_alias(k)] = v
            else:
                profile_attributes[k] = v
        provider = Provider.create(**provider_attributes)
        profile_attributes["provider"] = provider
        return ProfileAttributes(**profile_attributes)

    def set_attribute(self, key, value):
        if key in Provider.keys() and not isinstance(value, Provider):
            setattr(self.provider, key, value)
        else:
            setattr(self, key, value)


class BaseProfile(ABC):
    """
    BaseProfile is an abstract base class representing a Profile
    for Select AI's interactions with AI service providers (LLMs).
    Use either select_ai.Profile or select_ai.AsyncProfile to
    instantiate an AI profile object.

    :param str profile_name : Name of the profile

    :param select_ai.ProfileAttributes attributes:
     Object specifying AI profile attributes

    :param str description: Description of the profile

    :param bool merge: Fetches the profile
     from database, merges the non-null attributes and saves it back
     in the database. Default value is False

    :param bool replace: Replaces the profile and attributes
     in the database. Default value is False

    :param bool  raise_error_if_exists: Raise ProfileExistsError
     if profile exists in the database and replace = False and
     merge = False. Default value is True

    """

    def __init__(
        self,
        profile_name: Optional[str] = None,
        attributes: Optional[ProfileAttributes] = None,
        description: Optional[str] = None,
        merge: Optional[bool] = False,
        replace: Optional[bool] = False,
        raise_error_if_exists: Optional[bool] = True,
    ):
        """Initialize a base profile"""
        self.profile_name = profile_name
        if attributes and not isinstance(attributes, ProfileAttributes):
            raise TypeError(
                "'attributes' must be an object of type "
                "select_ai.ProfileAttributes"
            )
        self.attributes = attributes
        self.description = description
        self.merge = merge
        self.replace = replace
        self.raise_error_if_exists = raise_error_if_exists

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(profile_name={self.profile_name}, "
            f"attributes={self.attributes}, description={self.description})"
        )


def no_data_for_prompt(result) -> bool:
    if result is None:
        return True
    if result == "No data found for the prompt.":
        return True
    return False


def validate_params_for_feedback(
    feedback_type: FeedbackType,
    feedback_content: str,
    prompt_spec: Tuple[str, Action] = None,
    sql_id: Optional[str] = None,
    response: Optional[str] = None,
    operation: Optional[FeedbackOperation] = FeedbackOperation.ADD,
):
    if sql_id and prompt_spec:
        raise AttributeError("Either sql_id or prompt_spec must be specified")
    if not sql_id and not prompt_spec:
        raise AttributeError("Either sql_id or prompt_spec must be specified")
    parameters = {
        "feedback_type": feedback_type.value,
        "feedback_content": feedback_content,
        "operation": operation.value,
    }
    if prompt_spec:
        prompt, action = prompt_spec
        if action not in (Action.RUNSQL, Action.SHOWSQL, Action.EXPLAINSQL):
            raise AttributeError(
                "'action' must be one of 'RUNSQL', 'SHOWSQL' or 'EXPLAINSQL'"
            )
        if (
            operation == FeedbackOperation.ADD
            and feedback_type == FeedbackType.NEGATIVE
            and response is None
        ):
            raise AttributeError(
                "'response' must be specified if feedback_type is NEGATIVE"
            )
        sql_text = "select ai {} {}".format(action, prompt)
        parameters["sql_text"] = sql_text
    elif sql_id:
        parameters["sql_id"] = sql_id
    return parameters


def validate_params_for_summary(
    prompt: str = None,
    content: str = None,
    location_uri: str = None,
    credential_name: str = None,
    params: SummaryParams = None,
):
    if content and location_uri:
        raise AttributeError(
            "Either content or location_uri must be specified"
        )
    if not content and not location_uri:
        raise AttributeError(
            "Either content or location_uri must be specified"
        )
    parameters = {}
    if content:
        parameters["content"] = content
    if location_uri:
        parameters["location_uri"] = location_uri
    if credential_name:
        parameters["credential_name"] = credential_name
    if prompt:
        parameters["prompt"] = prompt
    if params:
        parameters["parameters"] = params.json()
    return parameters
