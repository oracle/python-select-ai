import json
from dataclasses import replace as dataclass_replace
from typing import Iterator, Mapping, Optional, Union

import oracledb
import pandas

from select_ai._base import BaseProfile
from select_ai.action import Action
from select_ai.conversation import ConversationAttributes
from select_ai.db import cursor
from select_ai.errors import ProfileNotFoundError, VectorIndexNotFoundError
from select_ai.provider import ProviderAttributes
from select_ai.sql import (
    GET_USER_AI_PROFILE_ATTRIBUTES,
    GET_USER_VECTOR_INDEX_ATTRIBUTES,
    LIST_USER_AI_PROFILES,
    LIST_USER_VECTOR_INDEXES_BY_PROFILE,
)
from select_ai.synthetic_data import SyntheticDataAttributes
from select_ai.vector_index import VectorIndex, VectorIndexAttributes


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
        if self.profile_name is not None:
            if self.fetch_and_merge_attributes:
                try:
                    saved_attributes = self.fetch_attributes(
                        profile_name=self.profile_name
                    )
                except ProfileNotFoundError:
                    self.replace = False
                    if self.attributes is None:
                        raise ValueError("Missing attributes")
                else:
                    self.replace = True
                    if self.attributes is not None:
                        # Replace attributes passed during __init__()
                        self.attributes = dataclass_replace(
                            saved_attributes,
                            **self.attributes.dict(filter_null=True),
                        )
                    else:
                        self.attributes = saved_attributes

            self.create(replace=self.replace, description=self.description)

    @staticmethod
    def fetch_attributes(profile_name) -> ProviderAttributes:
        """Fetch AI profile attributes from the Database

        :param str profile_name: Name of the profile
        :return: select_ai.provider.ProviderAttributes
        :raises: ProfileNotFoundError
        """
        json_attributes = ["object_list"]
        with cursor() as cr:
            cr.execute(
                GET_USER_AI_PROFILE_ATTRIBUTES,
                profile_name=profile_name.upper(),
            )
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB) and k in json_attributes:
                        post_processed_attributes[k] = json.loads(v.read())
                    elif isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return ProviderAttributes.create(**post_processed_attributes)
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    def create(
        self, replace: Optional[int] = False, description: Optional[str] = None
    ) -> None:
        """Create an AI Profile in the Database

        :param bool replace: Set True to replace else False
        :param description: The profile description
        :return: None
        :raises: oracledb.DatabaseError
        """

        parameters = {
            "profile_name": self.profile_name,
            "attributes": self.attributes.json(),
        }
        if description:
            parameters["description"] = description

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_PROFILE",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if "already exists" in error.message.lower() and replace:
                    self.drop(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_PROFILE",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    def drop(self, force=False) -> None:
        """Drop an AI profile from the database

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
    def from_db(cls, profile_name: str) -> "Profile":
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
                attributes = ProviderAttributes.create(**dict(attributes))
                return cls(profile_name=profile_name, attributes=attributes)
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    @classmethod
    def list(cls, profile_name_pattern: str) -> Iterator["Profile"]:
        """List AI Profiles saved in the database

        :param str profile_name_pattern: Regular expressions can be used
        to specify a pattern. Function REGEXP_LIKE is used to perform the
        match

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
                attributes = cls.fetch_attributes(profile_name=profile_name)
                yield cls(
                    profile_name=profile_name,
                    description=description,
                    attributes=attributes,
                )

    def generate(
        self,
        prompt: str,
        action: Optional[Action] = Action.RUNSQL,
        params: Mapping = None,
    ):
        """Perform AI translation using this profile

        :param str prompt: Natural language prompt to translate
        :param select_ai.profile.Action action:
        :param params: Parameters to include in the LLM request. For e.g.
         conversation_id for context-aware chats
        :return: Union[pandas.DataFrame, str]
        """
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

    def chat(self, prompt: str, params: Mapping = None) -> str:
        """Chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return self.generate(prompt, action=Action.CHAT, params=params)

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

    def create_vector_index(
        self,
        index_name: str,
        attributes: VectorIndexAttributes,
        description: str = Optional[None],
        replace: Optional[int] = False,
    ):
        """Create a vector index in the database and populates it with data
        from an object store bucket using an async scheduler job

        :param str index_name: Name of the vector index

        :param select_ai.VectorIndexAttributes attributes: Attributes of the
        vector index

        :param str description: Description for the vector index

        :param bool replace: Replace vector index if it exists

        :return: None
        """

        if attributes.profile_name is None:
            attributes.profile_name = self.profile_name

        parameters = {
            "index_name": index_name,
            "attributes": attributes.json(),
        }

        if description:
            parameters["description"] = description

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if "already exists" in error.message.lower() and replace:
                    self.drop_vector_index(force=True, index_name=index_name)
                    cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    @staticmethod
    def drop_vector_index(
        index_name: str,
        include_data: Optional[int] = True,
        force: Optional[int] = False,
    ):
        """This procedure removes a vector store index.

        :param str index_name: Name of the vector index

        :param bool include_data: Indicates whether to delete
         both the customer's vector store and vector index
         along with the vector index object.

        :param bool force: Indicates whether to ignore errors
        that occur if the vector index does not exist.

        :return: None

        :raises: oracledb.DatabaseError

        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DROP_VECTOR_INDEX",
                keyword_parameters={
                    "index_name": index_name,
                    "include_data": include_data,
                    "force": force,
                },
            )

    @staticmethod
    def enable_vector_index(index_name: str):
        """This procedure enables or activates a previously disabled vector
        index object. Generally, when you create a vector index, by default
        it is enabled such that the AI profile can use it to perform indexing
        and searching.

        :param str index_name: Name of the vector index
        :return: None
        :raises: oracledb.DatabaseError

        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": index_name},
            )

    @staticmethod
    def disable_vector_index(index_name: str):
        """This procedure disables a vector index object in the current
        database. When disabled, an AI profile cannot use the vector index,
        and the system does not load data into the vector store as new data
        is added to the object store and does not perform indexing, searching
        or querying based on the index.

        :param str index_name: Name of the vector index
        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": index_name},
            )

    @staticmethod
    def update_vector_index(
        index_name: str,
        attribute_name: str,
        attribute_value: Union[str, int, float],
    ):
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute.

        :param str index_name: Name of the vector index
        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value
        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters={
                    "index_name": index_name,
                    "attribute_name": attribute_name,
                    "attribute_value": attribute_value,
                },
            )

    @staticmethod
    def fetch_vector_index_attributes(
        index_name: str,
    ) -> VectorIndexAttributes:
        """Fetch attributes of a vector index

        :param str index_name: Name of the vector index
        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        with cursor() as cr:
            cr.execute(GET_USER_VECTOR_INDEX_ATTRIBUTES, index_name=index_name)
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return VectorIndexAttributes(**post_processed_attributes)
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    def list_vector_indexes(
        self, index_name_pattern: str
    ) -> Iterator[VectorIndex]:
        """List Vector Indexes

        :param str index_name_pattern: Regular expressions can be used
        to specify a pattern. Function REGEXP_LIKE is used to perform the
        match

        :return: Iterator[VectorIndex]

        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_VECTOR_INDEXES_BY_PROFILE,
                profile_name=self.profile_name,
                index_name_pattern=index_name_pattern,
            )
            for row in cr.fetchall():
                index_name = row[0]
                description = row[1].read()  # Oracle.LOB
                attributes = Profile.fetch_vector_index_attributes(
                    index_name=index_name
                )
                yield VectorIndex(
                    index_name=index_name,
                    description=description,
                    attributes=attributes,
                )

    def generate_synthetic_data(
        self, synthetic_data_attributes: SyntheticDataAttributes
    ):
        """Generate synthetic data for a single table, multiple tables or a
        full schema.

        :param select_ai.SyntheticDataAttributes synthetic_data_attributes:
        :return: None
        :raises: oracledb.DatabaseError

        """
        keyword_parameters = synthetic_data_attributes.prepare()
        keyword_parameters["profile_name"] = self.profile_name
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA",
                keyword_parameters=keyword_parameters,
            )

    @staticmethod
    def create_conversation(
        conversation_attributes: ConversationAttributes,
    ) -> str:
        """Creates a new conversation and returns the conversation_id
        to be used in context-aware conversations with LLMs

        :param select_ai.ConversationAttributes conversation_attributes:
         Conversation Attributes

        :return: conversation_id
        """
        with cursor() as cr:
            conversation_id = cr.callfunc(
                "DBMS_CLOUD_AI.CREATE_CONVERSATION",
                oracledb.DB_TYPE_VARCHAR,
                keyword_parameters={
                    "attributes": conversation_attributes.json()
                },
            )
        return conversation_id
