# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from contextlib import asynccontextmanager
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

from select_ai._validations import validate_user_or_role_name
from select_ai.action import Action
from select_ai.base_profile import (
    BaseProfile,
    ProfileAttributes,
    convert_json_rows_to_df,
    validate_params_for_feedback,
    validate_params_for_summary,
)
from select_ai.conversation import AsyncConversation
from select_ai.db import (
    AsyncConnectionManager,
    async_cursor,
    async_get_connection,
)
from select_ai.errors import (
    ProfileAttributesEmptyError,
    ProfileNotFoundError,
)
from select_ai.feedback import (
    FeedbackOperation,
    FeedbackType,
)
from select_ai.provider import Provider
from select_ai.sql import (
    GET_ALL_AI_PROFILE,
    GET_ALL_AI_PROFILE_ATTRIBUTES,
    LIST_ALL_AI_PROFILES,
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
                saved_description, saved_owner = (
                    await self._get_profile_description(
                        profile_name=self.profile_name,
                        owner=self.owner,
                    )
                )
                self.owner = saved_owner
                profile_exists = True
                saved_attributes = await self._get_attributes(
                    profile_name=self.profile_name,
                    owner=self.owner,
                    raise_on_empty=True,
                )
                self._raise_error_if_profile_exists()
            except ProfileAttributesEmptyError:
                if self.raise_error_on_empty_attributes:
                    raise
            except ProfileNotFoundError:
                if self.attributes is None and self.description is None:
                    raise
            else:
                self._merge_attributes(saved_attributes, saved_description)
            if self.replace or not profile_exists:
                await self.create(replace=self.replace)
        else:  # profile name is None:
            if self.attributes is not None or self.description is not None:
                raise ValueError("'profile_name' cannot be empty or None")
        return self

    @staticmethod
    async def _get_profile_description(
        profile_name: str, owner: Optional[str] = None
    ) -> Tuple[Union[str, None], str]:
        """Get a profile description and owner from ALL_CLOUD_AI_PROFILES.

        :param str profile_name: Name of profile
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :return: Tuple containing the profile description and owner.
        :raises: ProfileNotFoundError

        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_ALL_AI_PROFILE,
                profile_name=profile_name.upper(),
                owner=owner.upper() if owner else None,
            )
            profile = await cr.fetchone()
            if profile:
                if profile[1] is not None:
                    description = await profile[1].read()
                else:
                    description = None
                return description, profile[2]
            else:
                raise ProfileNotFoundError(profile_name)

    @staticmethod
    async def _get_attributes(
        profile_name: str,
        owner: Optional[str] = None,
        raise_on_empty: bool = True,
    ) -> Union[ProfileAttributes, None]:
        """Asynchronously gets AI profile attributes from the Database

        :param str profile_name: Name of the profile
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :param bool raise_on_empty: Raise an error if attributes are empty
        :return: select_ai.provider.ProviderAttributes
        :raises: select_ai.errors.ProfileAttributesEmptyError

        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_ALL_AI_PROFILE_ATTRIBUTES,
                profile_name=profile_name.upper(),
                owner=owner.upper() if owner else None,
            )
            attributes = await cr.fetchall()
            if attributes:
                return await ProfileAttributes.async_create(**dict(attributes))
            else:
                if raise_on_empty:
                    raise ProfileAttributesEmptyError(
                        profile_name=profile_name
                    )
                return None

    async def get_attributes(self) -> ProfileAttributes:
        """Asynchronously gets AI profile attributes from the Database

        :return: select_ai.provider.ProviderAttributes
        :raises: ProfileNotFoundError
        """
        return await self._get_attributes(
            profile_name=self.profile_name,
            owner=self.owner,
        )

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
            for k, v in attribute_value.profile_dict().items():
                await self._set_attribute(Provider.key_alias(k), v)
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

    @staticmethod
    async def _delete(profile_name: str, force: bool = False):
        """
        Internal method to delete AI profile from the database
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DROP_PROFILE",
                keyword_parameters={
                    "profile_name": profile_name,
                    "force": force,
                },
            )

    async def delete(self, force=False) -> None:
        """Asynchronously deletes an AI profile from the database

        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError
        """
        await self._delete(profile_name=self.profile_name, force=force)

    async def enable(self) -> None:
        """Asynchronously enable this AI profile in the database.

        :return: None
        :raises: oracledb.DatabaseError
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_PROFILE",
                keyword_parameters={"profile_name": self.profile_name},
            )

    async def disable(self) -> None:
        """Asynchronously disable this AI profile in the database.

        :return: None
        :raises: oracledb.DatabaseError
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_PROFILE",
                keyword_parameters={"profile_name": self.profile_name},
            )

    async def grant_access(self, user_or_role_name: str) -> None:
        """Asynchronously grant a user or role access to this AI profile."""
        user_or_role_name = validate_user_or_role_name(user_or_role_name)
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.GRANT_PROFILE_ACCESS",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "user_or_role_name": user_or_role_name,
                },
            )

    async def revoke_access(self, user_or_role_name: str) -> None:
        """Asynchronously revoke a user or role's profile access."""
        user_or_role_name = validate_user_or_role_name(user_or_role_name)
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.REVOKE_PROFILE_ACCESS",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "user_or_role_name": user_or_role_name,
                },
            )

    @classmethod
    async def delete_profile(cls, profile_name: str, force: bool = False):
        """Asynchronously deletes an AI profile from the database

        :param str profile_name: Name of the AI profile
        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError
        """
        await cls._delete(profile_name=profile_name, force=force)

    @classmethod
    async def fetch(
        cls, profile_name: str, owner: Optional[str] = None
    ) -> "AsyncProfile":
        """Asynchronously create an AI Profile object from attributes
        saved in the database

        :param str profile_name: Name of the AI profile.
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        return await cls(
            profile_name,
            owner=owner,
            raise_error_if_exists=False,
        )

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
        cls,
        profile_name_pattern: str = ".*",
        owner: Optional[str] = None,
    ) -> AsyncGenerator["AsyncProfile", None]:
        """Asynchronously list AI Profiles saved in the database.

        :param str profile_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all AI profiles.
        :param str owner: Owner of shared profiles. Defaults to current schema.

        :return: Iterator[Profile]
        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_ALL_AI_PROFILES,
                profile_name_pattern=profile_name_pattern,
                owner=owner.upper() if owner else None,
            )
            rows = await cr.fetchall()
            for row in rows:
                profile_name = row[0]
                yield await cls(
                    profile_name=profile_name,
                    owner=row[2],
                    raise_error_if_exists=False,
                    raise_error_on_empty_attributes=False,
                )

    async def _generate_with_cursor(
        self,
        cr,
        prompt: str,
        action=Action.SHOWSQL,
        params: Mapping = None,
        attributes: Mapping = None,
    ) -> Union[pandas.DataFrame, str, None]:
        """Asynchronously perform AI translation using this profile

        :param str prompt: Natural language prompt to translate
        :param select_ai.profile.Action action:
        :param params: Parameters to include in the LLM request. For e.g.
         conversation_id for context-aware chats
        :param Mapping attributes: Profile attributes to override for this
         request
        :return: Union[pandas.DataFrame, str]
        """
        parameters = self._generate_parameters(
            prompt, action, params, attributes
        )

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
            return convert_json_rows_to_df(result)
        else:
            return result

    def _generate_parameters(
        self,
        prompt: str,
        action,
        params: Mapping = None,
        attributes: Mapping = None,
    ) -> Mapping:
        if not prompt:
            raise ValueError("prompt cannot be empty or None")

        parameters = {
            "prompt": prompt,
            "action": action,
            "profile_name": self.profile_name,
        }
        if params:
            parameters["params"] = json.dumps(params)
        if attributes is not None:
            if not isinstance(attributes, Mapping):
                raise TypeError("'attributes' must be a mapping")
            parameters["attributes"] = json.dumps(attributes)
        return parameters

    async def _generate_stream(
        self,
        prompt: str,
        action,
        params: Mapping = None,
        chunk_size: int = 8192,
        attributes: Mapping = None,
    ) -> AsyncGenerator[str, None]:
        async with async_cursor() as cr:
            async for chunk in self._generate_stream_with_cursor(
                cr,
                prompt=prompt,
                action=action,
                params=params,
                chunk_size=chunk_size,
                attributes=attributes,
            ):
                yield chunk

    async def _generate_stream_with_cursor(
        self,
        cr,
        prompt: str,
        action,
        params: Mapping = None,
        chunk_size: int = 8192,
        attributes: Mapping = None,
    ) -> AsyncGenerator[str, None]:
        if action == Action.RUNSQL:
            raise ValueError("stream=True is not supported for run_sql")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        parameters = self._generate_parameters(
            prompt, action, params, attributes
        )
        data = await cr.callfunc(
            "DBMS_CLOUD_AI.GENERATE",
            oracledb.DB_TYPE_CLOB,
            keyword_parameters=parameters,
        )
        if data is None:
            return

        offset = 1
        while True:
            chunk = await data.read(offset=offset, amount=chunk_size)
            if not chunk:
                break
            yield chunk
            offset += len(chunk)

    async def generate(
        self,
        prompt: str,
        action=Action.SHOWSQL,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[pandas.DataFrame, str, AsyncGenerator[str, None], None]:
        """Asynchronously perform AI translation using this profile

        :param str prompt: Natural language prompt to translate
        :param select_ai.profile.Action action:
        :param params: Parameters to include in the LLM request. For e.g.
         conversation_id for context-aware chats
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: Union[pandas.DataFrame, str]
        """
        if stream:
            return self._generate_stream(
                prompt, action, params, chunk_size, attributes
            )
        async with async_cursor() as cr:
            return await self._generate_with_cursor(
                cr,
                prompt=prompt,
                action=action,
                params=params,
                attributes=attributes,
            )

    async def chat(
        self,
        prompt,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Asynchronously chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return await self.generate(
            prompt,
            action=Action.CHAT,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

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
            async with AsyncSession(
                async_profile=self, params=params
            ) as async_session:
                yield async_session
        finally:
            if delete:
                await conversation.delete()

    async def narrate(
        self,
        prompt,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return await self.generate(
            prompt,
            action=Action.NARRATE,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    async def explain_sql(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ):
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return await self.generate(
            prompt,
            action=Action.EXPLAINSQL,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    async def run_sql(
        self,
        prompt,
        params: Mapping = None,
        *,
        attributes: Mapping = None,
    ) -> pandas.DataFrame:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :return: pandas.DataFrame
        """
        return await self.generate(
            prompt,
            action=Action.RUNSQL,
            params=params,
            attributes=attributes,
        )

    async def show_sql(
        self,
        prompt,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ):
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return await self.generate(
            prompt,
            action=Action.SHOWSQL,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    async def show_prompt(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ):
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return await self.generate(
            prompt,
            action=Action.SHOWPROMPT,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
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
        *,
        attributes: Mapping = None,
    ) -> List[Union[str, pandas.DataFrame]]:
        """Send Multiple prompts in a single roundtrip to the Database

        :param List[Tuple[str, Action]] prompt_specifications: List of
         2-element tuples. First element is the prompt and second is the
         corresponding action

        :param bool continue_on_error: True to continue on error else False
        :param Mapping attributes: Profile attributes to override for every
         request in the pipeline
        :return: List[Union[str, pandas.DataFrame]]
        """
        serialized_attributes = None
        if attributes is not None:
            if not isinstance(attributes, Mapping):
                raise TypeError("'attributes' must be a mapping")
            serialized_attributes = json.dumps(attributes)

        pipeline = oracledb.create_pipeline()
        for prompt, action in prompt_specifications:
            parameters = {
                "prompt": prompt,
                "action": action,
                "profile_name": self.profile_name,
            }
            if serialized_attributes is not None:
                parameters["attributes"] = serialized_attributes
            pipeline.add_callfunc(
                "DBMS_CLOUD_AI.GENERATE",
                return_type=oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        async with async_get_connection() as async_connection:
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

    async def translate(
        self,
        text: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
    ) -> Union[str, None]:
        """
        Translate text using the supplied languages or the profile defaults.

        :param str text: Text to translate
        :param str source_language: Source language. When omitted, the profile
         value is used; if the profile does not define one, the provider
         detects the source language.
        :param str target_language: Target language. When omitted, the profile
         value is used.
        :return: str
        """
        parameters = {
            "profile_name": self.profile_name,
            "text": text,
            "source_language": source_language,
            "target_language": target_language,
        }
        async with async_cursor() as cr:
            data = await cr.callfunc(
                "DBMS_CLOUD_AI.TRANSLATE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        if data is not None:
            result = await data.read()
            return result
        return None


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
        self._conn = None
        self._conn_cm = None
        self._cursor = None

    async def chat(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        if stream:
            return self.async_profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.CHAT,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt=prompt,
            action=Action.CHAT,
            params=self.params,
            attributes=attributes,
        )

    async def narrate(
        self,
        prompt,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.async_profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.NARRATE,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.NARRATE,
            params=self.params,
            attributes=attributes,
        )

    async def explain_sql(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.async_profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.EXPLAINSQL,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.EXPLAINSQL,
            params=self.params,
            attributes=attributes,
        )

    async def run_sql(
        self, prompt: str, *, attributes: Mapping = None
    ) -> pandas.DataFrame:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :return: pandas.DataFrame
        """
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.RUNSQL,
            params=self.params,
            attributes=attributes,
        )

    async def show_sql(
        self,
        prompt,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.async_profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.SHOWSQL,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.SHOWSQL,
            params=self.params,
            attributes=attributes,
        )

    async def show_prompt(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param bool stream: Return an async iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.async_profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.SHOWPROMPT,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return await self.async_profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.SHOWPROMPT,
            params=self.params,
            attributes=attributes,
        )

    async def __aenter__(self):
        self._conn_cm = AsyncConnectionManager().get_connection()
        self._conn = await self._conn_cm.__aenter__()
        self._cursor = self._conn.cursor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._cursor is not None:
            self._cursor.close()
        if self._conn_cm is not None:
            await self._conn_cm.__aexit__(exc_type, exc_val, exc_tb)
        self._conn = None
        self._conn_cm = None
        self._cursor = None
