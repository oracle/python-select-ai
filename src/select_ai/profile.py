# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from contextlib import contextmanager
from dataclasses import replace as dataclass_replace
from typing import Iterator, Mapping, Optional, Union

import oracledb
import pandas

from select_ai import Conversation
from select_ai.action import Action
from select_ai.base_profile import BaseProfile, ProfileAttributes
from select_ai.db import cursor
from select_ai.errors import ProfileExistsError, ProfileNotFoundError
from select_ai.provider import Provider
from select_ai.sql import (
    GET_USER_AI_PROFILE,
    GET_USER_AI_PROFILE_ATTRIBUTES,
    LIST_USER_AI_PROFILES,
)
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
                saved_attributes = self._get_attributes(
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

                if self.description is None:
                    self.description = self._get_profile_description(
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
                self.create(replace=self.replace)
        else:  # profile name is None
            if self.attributes is not None or self.description is not None:
                raise ValueError(
                    "Attribute 'profile_name' cannot be empty or None"
                )

    @staticmethod
    def _get_profile_description(profile_name) -> Union[str, None]:
        """Get description of profile from USER_CLOUD_AI_PROFILES

        :param str profile_name:
        :return: Union[str, None] profile description
        :raises: ProfileNotFoundError
        """
        with cursor() as cr:
            cr.execute(GET_USER_AI_PROFILE, profile_name=profile_name.upper())
            profile = cr.fetchone()
            if profile:
                if profile[1] is not None:
                    return profile[1].read()
                else:
                    return None
            else:
                raise ProfileNotFoundError(profile_name)

    @staticmethod
    def _get_attributes(profile_name) -> ProfileAttributes:
        """Get AI profile attributes from the Database

        :param str profile_name: Name of the profile
        :return: select_ai.ProfileAttributes
        :raises: ProfileNotFoundError
        """
        with cursor() as cr:
            cr.execute(
                GET_USER_AI_PROFILE_ATTRIBUTES,
                profile_name=profile_name.upper(),
            )
            attributes = cr.fetchall()
            if attributes:
                return ProfileAttributes.create(**dict(attributes))
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    def get_attributes(self) -> ProfileAttributes:
        """Get AI profile attributes from the Database

        :return: select_ai.ProfileAttributes
        """
        return self._get_attributes(profile_name=self.profile_name)

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
            for k, v in attribute_value.dict().items():
                self._set_attribute(k, v)
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
        self.attributes = attributes
        parameters = {
            "profile_name": self.profile_name,
            "attributes": self.attributes.json(),
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTES", keyword_parameters=parameters
            )

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

    def delete(self, force=False) -> None:
        """Deletes an AI profile from the database

        :param bool force: Ignores errors if AI profile does not exist.
        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DROP_PROFILE",
                keyword_parameters={
                    "profile_name": self.profile_name,
                    "force": force,
                },
            )

    @classmethod
    def _from_db(cls, profile_name: str) -> "Profile":
        """Create a Profile object from attributes saved in the database

        :param str profile_name:
        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        with cursor() as cr:
            cr.execute(
                GET_USER_AI_PROFILE_ATTRIBUTES, profile_name=profile_name
            )
            attributes = cr.fetchall()
            if attributes:
                attributes = ProfileAttributes.create(**dict(attributes))
                return cls(profile_name=profile_name, attributes=attributes)
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    @classmethod
    def list(cls, profile_name_pattern: str = ".*") -> Iterator["Profile"]:
        """List AI Profiles saved in the database.

        :param str profile_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all AI profiles.

        :return: Iterator[Profile]
        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_AI_PROFILES,
                profile_name_pattern=profile_name_pattern,
            )
            for row in cr.fetchall():
                profile_name = row[0]
                description = row[1]
                attributes = cls._get_attributes(profile_name=profile_name)
                yield cls(
                    profile_name=profile_name,
                    description=description,
                    attributes=attributes,
                    raise_error_if_exists=False,
                )

    def generate(
        self,
        prompt: str,
        action: Optional[Action] = Action.RUNSQL,
        params: Mapping = None,
    ) -> Union[pandas.DataFrame, str, None]:
        """Perform AI translation using this profile

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
        with cursor() as cr:
            data = cr.callfunc(
                "DBMS_CLOUD_AI.GENERATE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        if data is not None:
            return data.read()
        return None

    def chat(self, prompt: str, params: Mapping = None) -> str:
        """Chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.CHAT, params=params)

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
            session = Session(profile=self, params=params)
            yield session
        finally:
            if delete:
                conversation.delete()

    def narrate(self, prompt: str, params: Mapping = None) -> str:
        """Narrate the result of the SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.NARRATE, params=params)

    def explain_sql(self, prompt: str, params: Mapping = None) -> str:
        """Explain the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.EXPLAINSQL, params=params)

    def run_sql(self, prompt: str, params: Mapping = None) -> pandas.DataFrame:
        """Run the generate SQL statement and return a pandas Dataframe built
        using the result set

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: pandas.DataFrame
        """
        data = json.loads(
            self.generate(prompt, action=Action.RUNSQL, params=params)
        )
        return pandas.DataFrame(data)

    def show_sql(self, prompt: str, params: Mapping = None) -> str:
        """Show the generated SQL

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.SHOWSQL, params=params)

    def show_prompt(self, prompt: str, params: Mapping = None) -> str:
        """Show the prompt sent to LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.SHOWPROMPT, params=params)

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

    def chat(self, prompt: str):
        # params = {"conversation_id": self.conversation_id}
        return self.profile.chat(prompt=prompt, params=self.params)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
