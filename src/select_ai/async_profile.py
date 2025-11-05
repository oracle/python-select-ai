# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from contextlib import asynccontextmanager
from dataclasses import replace as dataclass_replace
from typing import (
    AsyncGenerator,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

import oracledb
import pandas

from select_ai.action import Action
from select_ai.base_profile import (
    BaseProfile,
    ProfileAttributes,
    no_data_for_prompt,
    validate_params_for_feedback,
    validate_params_for_summary,
)
from select_ai.conversation import AsyncConversation
from select_ai.db import async_cursor, async_get_connection
from select_ai.errors import ProfileExistsError, ProfileNotFoundError
from select_ai.feedback import (
    FeedbackOperation,
    FeedbackType,
)
from select_ai.provider import Provider
from select_ai.sql import (
    GET_USER_AI_PROFILE,
    GET_USER_AI_PROFILE_ATTRIBUTES,
    LIST_USER_AI_PROFILES,
)
from select_ai.summary import SummaryParams
from select_ai.synthetic_data import SyntheticDataAttributes

__all__ = ["AsyncProfile"]


class AsyncProfile(BaseProfile):
    """AsyncProfile defines methods to interact with the underlying AI Provider
    asynchronously.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_coroutine = self._init_profile()

    def __await__(self):
        coroutine = self._init_coroutine
        return coroutine.__await__()

    async def _init_profile(self):
        """Initializes AI profile based on the passed attributes

        :return: None
        :raises: oracledb.DatabaseError
        """
        if self.profile_name:
            profile_exists = False
            try:
                saved_attributes = await self._get_attributes(
                    profile_name=self.profile_name
                )
                profile_exists = True
                if not self.replace and not self.merge:
                    if (
                        self.attributes is not None
                        or self.description is not None
                    ):
                        if self.raise_error_if_exists:
                            raise ProfileExistsError(self.profile_name)

                if self.description is None and not self.replace:
                    self.description = await self._get_profile_description(
                        profile_name=self.profile_name
                    )
            except ProfileNotFoundError:
                if self.attributes is None and self.description is None:
                    raise
            else:
                if self.attributes is None:
                    self.attributes = saved_attributes
                if self.merge:
                    self.replace = True
                    if self.attributes is not None:
                        self.attributes = dataclass_replace(
                            saved_attributes,
                            **self.attributes.dict(exclude_null=True),
                        )
            if self.replace or not profile_exists:
                await self.create(replace=self.replace)
        else:  # profile name is None:
            if self.attributes is not None or self.description is not None:
                raise ValueError("'profile_name' cannot be empty or None")
        return self

    @staticmethod
    async def _get_profile_description(profile_name) -> Union[str, None]:
        """Get description of profile from USER_CLOUD_AI_PROFILES

        :param str profile_name: Name of profile
        :return: Description of profile
        :rtype: str
        :raises: ProfileNotFoundError

        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_PROFILE,
                profile_name=profile_name.upper(),
            )
            profile = await cr.fetchone()
            if profile is None:
                raise ProfileNotFoundError(profile_name)
            if profile:
                if profile[1] is not None:
                    return await profile[1].read()
                else:
                    return None
            else:
                raise ProfileNotFoundError(profile_name)

    @staticmethod
    async def _get_attributes(profile_name) -> ProfileAttributes:
        """Asynchronously gets AI profile attributes from the Database

        :param str profile_name: Name of the profile
        :return: select_ai.provider.ProviderAttributes
        :raises: ProfileNotFoundError

        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_PROFILE_ATTRIBUTES,
                profile_name=profile_name.upper(),
            )
            attributes = await cr.fetchall()
            if attributes:
                return await ProfileAttributes.async_create(**dict(attributes))
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    async def get_attributes(self) -> ProfileAttributes:
        """Asynchronously gets AI profile attributes from the Database

        :return: select_ai.provider.ProviderAttributes
        :raises: ProfileNotFoundError
        """
        return await self._get_attributes(profile_name=self.profile_name)

    async def _set_attribute(
        self,
        attribute_name: str,
        attribute_value: Union[bool, str, int, float],
    ):
        parameters = {
            "profile_name": self.profile_name,
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTE", keyword_parameters=parameters
            )

    async def set_attribute(
        self,
        attribute_name: str,
        attribute_value: Union[bool, str, int, float, Provider],
    ):
        """Updates AI profile attribute on the Python object and also
        saves it in the database

        :param str attribute_name: Name of the AI profile attribute
        :param Union[bool, str, int, float] attribute_value: Value of the
         profile attribute
        :return: None

        """
        self.attributes.set_attribute(attribute_name, attribute_value)
        if isinstance(attribute_value, Provider):
            for k, v in attribute_value.dict().items():
                await self._set_attribute(k, v)
        else:
            await self._set_attribute(attribute_name, attribute_value)

    async def set_attributes(self, attributes: ProfileAttributes):
        """Updates AI profile attributes on the Python object and also
        saves it in the database

        :param ProfileAttributes attributes: Object specifying AI profile
         attributes
        :return: None
        """
        if not isinstance(attributes, ProfileAttributes):
            raise TypeError(
                "'attributes' must be an object of type "
                "select_ai.ProfileAttributes"
            )
        parameters = {
            "profile_name": self.profile_name,
            "attributes": attributes.json(),
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTES", keyword_parameters=parameters
            )
        self.attributes = await self.get_attributes()

    async def create(self, replace: Optional[int] = False) -> None:
        """Asynchronously create an AI Profile in the Database

        :param bool replace: Set True to replace else False
        :return: None
        :raises: oracledb.DatabaseError
        """
        if self.attributes is None:
            raise AttributeError("Profile attributes cannot be None")
        parameters = {
            "profile_name": self.profile_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description
        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_PROFILE",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if error.code == 20046 and replace:
                    await self.delete(force=True)
                    await cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_PROFILE",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    async def delete(self, force=False) -> None:
        """Asynchronously deletes an AI profile from the database

        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError

        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DROP_PROFILE",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "force": force,
                },
            )

    @classmethod
    async def fetch(cls, profile_name: str) -> "AsyncProfile":
        """Asynchronously create an AI Profile object from attributes
        saved in the database

        :param str profile_name:
        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        return await cls(profile_name, raise_error_if_exists=False)

    async def _save_feedback(
        self,
        feedback_type: FeedbackType = None,
        prompt_spec: Tuple[str, Action] = None,
        sql_id: Optional[str] = None,
        response: Optional[str] = None,
        feedback_content: Optional[str] = None,
        operation: Optional[FeedbackOperation] = FeedbackOperation.ADD,
    ):
        """
        Internal method to provide feedback
        """
        params = validate_params_for_feedback(
            feedback_type=feedback_type,
            feedback_content=feedback_content,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
            response=response,
            operation=operation,
        )
        params["profile_name"] = self.profile_name
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.FEEDBACK", keyword_parameters=params
            )

    async def add_positive_feedback(
        self,
        prompt_spec: Optional[Tuple[str, Action]] = None,
        sql_id: Optional[str] = None,
    ):
        """
        Give positive feedback to the LLM

        :param Tuple[str, Action] prompt_spec:  First element is the prompt and
         second is the corresponding action
        :param str sql_id: SQL identifier from V$MAPPED_SQL view
        """
        await self._save_feedback(
            feedback_type=FeedbackType.POSITIVE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
        )

    async def add_negative_feedback(
        self,
        prompt_spec: Optional[Tuple[str, Action]] = None,
        sql_id: Optional[str] = None,
        response: Optional[str] = None,
        feedback_content: Optional[str] = None,
    ):
        """
        Give negative feedback to the LLM

        :param Tuple[str, Action] prompt_spec:  First element is the prompt and
         second is the corresponding action
        :param str sql_id: SQL identifier from V$MAPPED_SQL view
        :param str response: Expected SQL from LLM
        :param str feedback_content: Actual feedback in natural language
        """
        await self._save_feedback(
            feedback_type=FeedbackType.NEGATIVE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content,
        )

    async def delete_feedback(
        self,
        prompt_spec: Tuple[str, Action] = None,
        sql_id: Optional[str] = None,
    ):
        """
        Delete feedback from the database

        :param Tuple[str, Action] prompt_spec:  First element is the prompt and
         second is the corresponding action
        :param str sql_id: SQL identifier from V$MAPPED_SQL view

        """
        await self._save_feedback(
            operation=FeedbackOperation.DELETE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
        )

    @classmethod
    async def list(
        cls, profile_name_pattern: str = ".*"
    ) -> AsyncGenerator["AsyncProfile", None]:
        """Asynchronously list AI Profiles saved in the database.

        :param str profile_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all AI profiles.

        :return: Iterator[Profile]
        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_AI_PROFILES,
                profile_name_pattern=profile_name_pattern,
            )
            rows = await cr.fetchall()
            for row in rows:
                profile_name = row[0]
                yield await cls(
                    profile_name=profile_name, raise_error_if_exists=False
                )

    async def generate(
        self, prompt: str, action=Action.SHOWSQL, params: Mapping = None
    ) -> Union[pandas.DataFrame, str, None]:
        """Asynchronously perform AI translation using this profile

        :param str prompt: Natural language prompt to translate
        :param select_ai.profile.Action action:
        :param params: Parameters to include in the LLM request. For e.g.
         conversation_id for context-aware chats
        :return: Union[pandas.DataFrame, str]
        """
        if not prompt:
            raise ValueError("prompt cannot be empty or None")

        parameters = {
            "prompt": prompt,
            "action": action,
            "profile_name": self.profile_name,
            # "attributes": self.attributes.json(),
        }
        if params:
            parameters["params"] = json.dumps(params)

        async with async_cursor() as cr:
            data = await cr.callfunc(
                "DBMS_CLOUD_AI.GENERATE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        if data is not None:
            result = await data.read()
        else:
            result = None
        if action == Action.RUNSQL:
            if no_data_for_prompt(result):  # empty dataframe
                return pandas.DataFrame()
            return pandas.DataFrame(json.loads(result))
        else:
            return result

    async def chat(self, prompt, params: Mapping = None) -> str:
        """Asynchronously chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(prompt, action=Action.CHAT, params=params)

    @asynccontextmanager
    async def chat_session(
        self, conversation: AsyncConversation, delete: bool = False
    ):
        """Starts a new chat session for context-aware conversations

        :param AsyncConversation conversation: Conversation object to use for this
         chat session
        :param bool delete: Delete conversation after session ends

        """
        try:
            if (
                conversation.conversation_id is None
                and conversation.attributes is not None
            ):
                await conversation.create()
            params = {"conversation_id": conversation.conversation_id}
            async_session = AsyncSession(async_profile=self, params=params)
            yield async_session
        finally:
            if delete:
                await conversation.delete()

    async def narrate(self, prompt, params: Mapping = None) -> str:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(
            prompt, action=Action.NARRATE, params=params
        )

    async def explain_sql(self, prompt: str, params: Mapping = None):
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(
            prompt, action=Action.EXPLAINSQL, params=params
        )

    async def run_sql(
        self, prompt, params: Mapping = None
    ) -> pandas.DataFrame:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: pandas.DataFrame
        """
        return await self.generate(prompt, action=Action.RUNSQL, params=params)

    async def show_sql(self, prompt, params: Mapping = None):
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(
            prompt, action=Action.SHOWSQL, params=params
        )

    async def show_prompt(self, prompt: str, params: Mapping = None):
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(
            prompt, action=Action.SHOWPROMPT, params=params
        )

    async def summarize(
        self,
        content: str = None,
        prompt: str = None,
        location_uri: str = None,
        credential_name: str = None,
        params: SummaryParams = None,
    ) -> str:
        """Generate summary

        :param str prompt: Natural language prompt to guide the summary
         generation
        :param str content: Specifies the text you want to summarize
        :param str location_uri: Provides the URI where the text is stored or
         the path to a local file stored
        :param str credential_name: Identifies the credential object used to
         authenticate with the object store
        :param select_ai.summary.SummaryParams params: Parameters to include
         in the LLM request
        """
        parameters = validate_params_for_summary(
            prompt=prompt,
            location_uri=location_uri,
            content=content,
            credential_name=credential_name,
            params=params,
        )
        parameters["profile_name"] = self.profile_name
        async with async_cursor() as cr:
            data = await cr.callfunc(
                "DBMS_CLOUD_AI.SUMMARIZE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        return await data.read() if data else None

    async def generate_synthetic_data(
        self, synthetic_data_attributes: SyntheticDataAttributes
    ) -> None:
        """Generate synthetic data for a single table, multiple tables or a
        full schema.

        :param select_ai.SyntheticDataAttributes synthetic_data_attributes:
        :return: None
        :raises: oracledb.DatabaseError

        """
        if synthetic_data_attributes is None:
            raise ValueError("'synthetic_data_attributes' cannot be None")

        if not isinstance(synthetic_data_attributes, SyntheticDataAttributes):
            raise TypeError(
                "'synthetic_data_attributes' must be an object "
                "of type select_ai.SyntheticDataAttributes"
            )

        keyword_parameters = synthetic_data_attributes.prepare()
        keyword_parameters["profile_name"] = self.profile_name
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA",
                keyword_parameters=keyword_parameters,
            )

    async def run_pipeline(
        self,
        prompt_specifications: List[Tuple[str, Action]],
        continue_on_error: bool = False,
    ) -> List[Union[str, pandas.DataFrame]]:
        """Send Multiple prompts in a single roundtrip to the Database

        :param List[Tuple[str, Action]] prompt_specifications: List of
         2-element tuples. First element is the prompt and second is the
         corresponding action

        :param bool continue_on_error: True to continue on error else False
        :return: List[Union[str, pandas.DataFrame]]
        """
        pipeline = oracledb.create_pipeline()
        for prompt, action in prompt_specifications:
            parameters = {
                "prompt": prompt,
                "action": action,
                "profile_name": self.profile_name,
                # "attributes": self.attributes.json(),
            }
            pipeline.add_callfunc(
                "DBMS_CLOUD_AI.GENERATE",
                return_type=oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        async_connection = await async_get_connection()
        pipeline_results = await async_connection.run_pipeline(
            pipeline, continue_on_error=continue_on_error
        )
        responses = []
        for result in pipeline_results:
            if not result.error:
                lob_data = result.return_value
                data = await lob_data.read()
                responses.append(data)
            else:
                responses.append(result.error)
        return responses


class AsyncSession:
    """AsyncSession lets you persist request parameters across DBMS_CLOUD_AI
    requests. This is useful in context-aware conversations
    """

    def __init__(self, async_profile: AsyncProfile, params: Mapping):
        """

        :param async_profile: An AI Profile to use in this session
        :param params: Parameters to be persisted across requests
        """
        self.params = params
        self.async_profile = async_profile

    async def chat(self, prompt: str):
        return await self.async_profile.chat(prompt=prompt, params=self.params)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
