# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from contextlib import contextmanager
from typing import Generator, Mapping, Optional, Tuple, Union

import oracledb
import pandas

from select_ai import Conversation
from select_ai._validations import validate_user_or_role_name
from select_ai.action import Action
from select_ai.base_profile import (
    BaseProfile,
    ProfileAttributes,
    convert_json_rows_to_df,
    validate_params_for_feedback,
    validate_params_for_summary,
)
from select_ai.db import ConnectionManager, cursor
from select_ai.errors import (
    ProfileAttributesEmptyError,
    ProfileNotFoundError,
)
from select_ai.feedback import FeedbackOperation, FeedbackType
from select_ai.provider import Provider
from select_ai.sql import (
    GET_ALL_AI_PROFILE,
    GET_ALL_AI_PROFILE_ATTRIBUTES,
    LIST_ALL_AI_PROFILES,
)
from select_ai.summary import SummaryParams
from select_ai.synthetic_data import SyntheticDataAttributes


class Profile(BaseProfile):
    """Profile class represents an AI Profile. It defines
    attributes and methods to interact with the underlying
    AI Provider. All methods in this class are synchronous
    or blocking
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_profile()

    def _init_profile(self) -> None:
        """Initializes AI profile based on the passed attributes

        :return: None
        :raises: oracledb.DatabaseError
        """
        if self.profile_name:
            profile_exists = False
            try:
                saved_description, saved_owner = self._get_profile_description(
                    profile_name=self.profile_name,
                    owner=self.owner,
                )
                self.owner = saved_owner
                profile_exists = True
                saved_attributes = self._get_attributes(
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
                self.create(replace=self.replace)
        else:  # profile name is None
            if self.attributes is not None or self.description is not None:
                raise ValueError(
                    "Attribute 'profile_name' cannot be empty or None"
                )

    @staticmethod
    def _get_profile_description(
        profile_name: str, owner: Optional[str] = None
    ) -> Tuple[Union[str, None], str]:
        """Get a profile description and owner from ALL_CLOUD_AI_PROFILES.

        :param str profile_name: Name of the profile.
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :return: Tuple containing the profile description and owner.
        :raises: ProfileNotFoundError
        """
        with cursor() as cr:
            cr.execute(
                GET_ALL_AI_PROFILE,
                profile_name=profile_name.upper(),
                owner=owner.upper() if owner else None,
            )
            profile = cr.fetchone()
            if profile:
                if profile[1] is not None:
                    description = profile[1].read()
                else:
                    description = None
                return description, profile[2]
            else:
                raise ProfileNotFoundError(profile_name)

    @staticmethod
    def _get_attributes(
        profile_name,
        owner: Optional[str] = None,
        raise_on_empty: bool = False,
    ) -> Union[ProfileAttributes, None]:
        """Get AI profile attributes from the Database

        :param str profile_name: Name of the profile
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :param bool raise_on_empty: Raise an error if attributes are empty
        :return: select_ai.ProfileAttributes
        :raises: select_ai.errors.ProfileAttributesEmptyError
        """
        with cursor() as cr:
            cr.execute(
                GET_ALL_AI_PROFILE_ATTRIBUTES,
                profile_name=profile_name.upper(),
                owner=owner.upper() if owner else None,
            )
            attributes = cr.fetchall()
            if attributes:
                return ProfileAttributes.create(**dict(attributes))
            else:
                if raise_on_empty:
                    raise ProfileAttributesEmptyError(
                        profile_name=profile_name
                    )
                return None

    def get_attributes(self) -> ProfileAttributes:
        """Get AI profile attributes from the Database

        :return: select_ai.ProfileAttributes
        """
        return self._get_attributes(
            profile_name=self.profile_name,
            owner=self.owner,
        )

    def _set_attribute(
        self,
        attribute_name: str,
        attribute_value: Union[bool, str, int, float],
    ):
        parameters = {
            "profile_name": self.profile_name,
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTE", keyword_parameters=parameters
            )

    def set_attribute(
        self,
        attribute_name: str,
        attribute_value: Union[bool, str, int, float, Provider],
    ):
        """Updates AI profile attribute on the Python object and also
        saves it in the database

        :param str attribute_name: Name of the AI profile attribute
        :param Union[bool, str, int, float, Provider] attribute_value: Value of
         the profile attribute
        :return: None

        """
        self.attributes.set_attribute(attribute_name, attribute_value)
        if isinstance(attribute_value, Provider):
            for k, v in attribute_value.profile_dict().items():
                self._set_attribute(Provider.key_alias(k), v)
        else:
            self._set_attribute(attribute_name, attribute_value)

    def set_attributes(self, attributes: ProfileAttributes):
        """Updates AI profile attributes on the Python object and also
        saves it in the database

        :param ProviderAttributes attributes: Object specifying AI profile
         attributes
        :return: None
        """
        if not isinstance(attributes, ProfileAttributes):
            raise TypeError(
                "'attributes' must be an object of type"
                " select_ai.ProfileAttributes"
            )
        parameters = {
            "profile_name": self.profile_name,
            "attributes": attributes.json(),
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTES", keyword_parameters=parameters
            )
        self.attributes = self.get_attributes()

    def create(self, replace: Optional[int] = False) -> None:
        """Create an AI Profile in the Database

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

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_PROFILE",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if error.code == 20046 and replace:
                    self.delete(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_PROFILE",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    @staticmethod
    def _delete(profile_name: str, force: bool = False):
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DROP_PROFILE",
                keyword_parameters={
                    "profile_name": profile_name,
                    "force": force,
                },
            )

    def delete(self, force=False) -> None:
        """Deletes an AI profile from the database

        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError
        """
        self._delete(profile_name=self.profile_name, force=force)

    def enable(self) -> None:
        """Enable this AI profile in the database.

        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_PROFILE",
                keyword_parameters={"profile_name": self.profile_name},
            )

    def disable(self) -> None:
        """Disable this AI profile in the database.

        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_PROFILE",
                keyword_parameters={"profile_name": self.profile_name},
            )

    def grant_access(self, user_or_role_name: str) -> None:
        """Grant a database user or role access to this AI profile.

        :param str user_or_role_name: Database user or role receiving access.
        :return: None
        :raises: oracledb.DatabaseError
        """
        user_or_role_name = validate_user_or_role_name(user_or_role_name)
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.GRANT_PROFILE_ACCESS",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "user_or_role_name": user_or_role_name,
                },
            )

    def revoke_access(self, user_or_role_name: str) -> None:
        """Revoke a database user or role's access to this AI profile.

        :param str user_or_role_name: Database user or role losing access.
        :return: None
        :raises: oracledb.DatabaseError
        """
        user_or_role_name = validate_user_or_role_name(user_or_role_name)
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.REVOKE_PROFILE_ACCESS",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "user_or_role_name": user_or_role_name,
                },
            )

    @classmethod
    def delete_profile(cls, profile_name: str, force: bool = False):
        """Class method to delete an AI profile from the database

        :param str profile_name: Name of the AI profile
        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError
        """
        cls._delete(profile_name=profile_name, force=force)

    @classmethod
    def fetch(
        cls, profile_name: str, owner: Optional[str] = None
    ) -> "Profile":
        """Create a proxy Profile object from fetched attributes saved in the
        database

        :param str profile_name: The name of the AI profile
        :param str owner: Owner of a shared profile. Defaults to current schema.
        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        return cls(
            profile_name,
            owner=owner,
            raise_error_if_exists=False,
        )

    def _save_feedback(
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
        with cursor() as cr:
            cr.callproc("DBMS_CLOUD_AI.FEEDBACK", keyword_parameters=params)

    def add_positive_feedback(
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
        self._save_feedback(
            feedback_type=FeedbackType.POSITIVE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
        )

    def add_negative_feedback(
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
        self._save_feedback(
            feedback_type=FeedbackType.NEGATIVE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content,
        )

    def delete_feedback(
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
        self._save_feedback(
            operation=FeedbackOperation.DELETE,
            prompt_spec=prompt_spec,
            sql_id=sql_id,
        )

    @classmethod
    def list(
        cls,
        profile_name_pattern: str = ".*",
        owner: Optional[str] = None,
    ) -> Generator["Profile", None, None]:
        """List AI Profiles saved in the database.

        :param str profile_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all AI profiles.
        :param str owner: Owner of shared profiles. Defaults to current schema.

        :return: Iterator[Profile]
        """
        with cursor() as cr:
            cr.execute(
                LIST_ALL_AI_PROFILES,
                profile_name_pattern=profile_name_pattern,
                owner=owner.upper() if owner else None,
            )
            for row in cr.fetchall():
                profile_name = row[0]
                yield cls(
                    profile_name=profile_name,
                    owner=row[2],
                    raise_error_if_exists=False,
                    raise_error_on_empty_attributes=False,
                )

    def _generate_with_cursor(
        self,
        cr,
        prompt: str,
        action: Optional[Action] = Action.RUNSQL,
        params: Mapping = None,
        attributes: Mapping = None,
    ) -> Union[pandas.DataFrame, str, None]:
        """Perform AI translation using this profile

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
        data = cr.callfunc(
            "DBMS_CLOUD_AI.GENERATE",
            oracledb.DB_TYPE_CLOB,
            keyword_parameters=parameters,
        )
        if data is not None:
            result = data.read()
        else:
            result = None
        if action == Action.RUNSQL:
            return convert_json_rows_to_df(result)
        else:
            return result

    def _generate_parameters(
        self,
        prompt: str,
        action: Optional[Action],
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

    def _generate_stream(
        self,
        prompt: str,
        action: Optional[Action],
        params: Mapping = None,
        chunk_size: int = 8192,
        attributes: Mapping = None,
    ) -> Generator[str, None, None]:
        with cursor() as cr:
            yield from self._generate_stream_with_cursor(
                cr,
                prompt=prompt,
                action=action,
                params=params,
                chunk_size=chunk_size,
                attributes=attributes,
            )

    def _generate_stream_with_cursor(
        self,
        cr,
        prompt: str,
        action: Optional[Action],
        params: Mapping = None,
        chunk_size: int = 8192,
        attributes: Mapping = None,
    ) -> Generator[str, None, None]:
        if action == Action.RUNSQL:
            raise ValueError("stream=True is not supported for run_sql")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")

        parameters = self._generate_parameters(
            prompt, action, params, attributes
        )
        data = cr.callfunc(
            "DBMS_CLOUD_AI.GENERATE",
            oracledb.DB_TYPE_CLOB,
            keyword_parameters=parameters,
        )
        if data is None:
            return

        offset = 1
        while True:
            chunk = data.read(offset=offset, amount=chunk_size)
            if not chunk:
                break
            yield chunk
            offset += len(chunk)

    def generate(
        self,
        prompt: str,
        action: Optional[Action] = Action.RUNSQL,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[pandas.DataFrame, str, Generator[str, None, None], None]:
        """Perform AI translation using this profile

        :param str prompt: Natural language prompt to translate
        :param select_ai.profile.Action action:
        :param params: Parameters to include in the LLM request. For e.g.
         conversation_id for context-aware chats
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: Union[pandas.DataFrame, str]
        """
        if stream:
            return self._generate_stream(
                prompt, action, params, chunk_size, attributes
            )
        with cursor() as cr:
            return self._generate_with_cursor(
                cr,
                prompt=prompt,
                action=action,
                params=params,
                attributes=attributes,
            )

    def chat(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return self.generate(
            prompt,
            action=Action.CHAT,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    @contextmanager
    def chat_session(self, conversation: Conversation, delete: bool = False):
        """Starts a new chat session for context-aware conversations

        :param Conversation conversation: Conversation object to use for this
         chat session
        :param bool delete: Delete conversation after session ends

        :return:
        """
        try:
            if (
                conversation.conversation_id is None
                and conversation.attributes is not None
            ):
                conversation.create()
            params = {"conversation_id": conversation.conversation_id}
            with Session(profile=self, params=params) as session:
                yield session
        finally:
            if delete:
                conversation.delete()

    def narrate(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return self.generate(
            prompt,
            action=Action.NARRATE,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    def explain_sql(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return self.generate(
            prompt,
            action=Action.EXPLAINSQL,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    def run_sql(
        self,
        prompt: str,
        params: Mapping = None,
        *,
        attributes: Mapping = None,
    ) -> pandas.DataFrame:
        """Run the generate SQL statement and return a pandas Dataframe built
        using the result set

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :return: pandas.DataFrame
        """
        return self.generate(
            prompt,
            action=Action.RUNSQL,
            params=params,
            attributes=attributes,
        )

    def show_sql(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return self.generate(
            prompt,
            action=Action.SHOWSQL,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    def show_prompt(
        self,
        prompt: str,
        params: Mapping = None,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param Mapping attributes: Profile attributes to override for this
         request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        return self.generate(
            prompt,
            action=Action.SHOWPROMPT,
            params=params,
            stream=stream,
            chunk_size=chunk_size,
            attributes=attributes,
        )

    def summarize(
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
        with cursor() as cr:
            data = cr.callfunc(
                "DBMS_CLOUD_AI.SUMMARIZE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        return data.read() if data else None

    def generate_synthetic_data(
        self, synthetic_data_attributes: SyntheticDataAttributes
    ) -> None:
        """Generate synthetic data for a single table, multiple tables or a
        full schema.

        :param select_ai.SyntheticDataAttributes synthetic_data_attributes:
        :return: None
        :raises: oracledb.DatabaseError

        """
        if synthetic_data_attributes is None:
            raise ValueError(
                "Param 'synthetic_data_attributes' cannot be None"
            )

        if not isinstance(synthetic_data_attributes, SyntheticDataAttributes):
            raise TypeError(
                "'synthetic_data_attributes' must be an object "
                "of type select_ai.SyntheticDataAttributes"
            )

        keyword_parameters = synthetic_data_attributes.prepare()
        keyword_parameters["profile_name"] = self.profile_name
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA",
                keyword_parameters=keyword_parameters,
            )

    def translate(
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
        with cursor() as cr:
            data = cr.callfunc(
                "DBMS_CLOUD_AI.TRANSLATE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        if data is not None:
            result = data.read()
            return result
        return None


class Session:
    """Session lets you persist request parameters across DBMS_CLOUD_AI
    requests. This is useful in context-aware conversations
    """

    def __init__(self, profile: Profile, params: Mapping):
        """

        :param profile: An AI Profile to use in this session
        :param params: Parameters to be persisted across requests
        """
        self.params = params
        self.profile = profile
        self._conn = None
        self._conn_cm = None
        self._cursor = None

    def chat(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        if stream:
            return self.profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.CHAT,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt=prompt,
            action=Action.CHAT,
            params=self.params,
            attributes=attributes,
        )

    def narrate(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.NARRATE,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.NARRATE,
            params=self.params,
            attributes=attributes,
        )

    def explain_sql(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.EXPLAINSQL,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.EXPLAINSQL,
            params=self.params,
            attributes=attributes,
        )

    def run_sql(
        self, prompt: str, *, attributes: Mapping = None
    ) -> pandas.DataFrame:
        """Run the generate SQL statement and return a pandas Dataframe built
        using the result set

        :param str prompt: Natural language prompt
        :return: pandas.DataFrame
        """
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.RUNSQL,
            params=self.params,
            attributes=attributes,
        )

    def show_sql(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.SHOWSQL,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.SHOWSQL,
            params=self.params,
            attributes=attributes,
        )

    def show_prompt(
        self,
        prompt: str,
        stream: bool = False,
        chunk_size: int = 8192,
        *,
        attributes: Mapping = None,
    ) -> Union[str, Generator[str, None, None]]:
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :param bool stream: Return an iterator of response chunks
        :param int chunk_size: Number of characters to read per stream chunk
        :return: str
        """
        if stream:
            return self.profile._generate_stream_with_cursor(
                self._cursor,
                prompt=prompt,
                action=Action.SHOWPROMPT,
                params=self.params,
                chunk_size=chunk_size,
                attributes=attributes,
            )
        return self.profile._generate_with_cursor(
            self._cursor,
            prompt,
            action=Action.SHOWPROMPT,
            params=self.params,
            attributes=attributes,
        )

    def __enter__(self):
        self._conn_cm = ConnectionManager().get_connection()
        self._conn = self._conn_cm.__enter__()
        self._cursor = self._conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cursor is not None:
            self._cursor.close()
        if self._conn_cm is not None:
            self._conn_cm.__exit__(exc_type, exc_val, exc_tb)
        self._conn = None
        self._conn_cm = None
        self._cursor = None
