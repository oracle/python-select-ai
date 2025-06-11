import json
from dataclasses import replace as dataclass_replace
from typing import (
    Any,
    AsyncGenerator,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

import oracledb
import pandas

from select_ai.action import Action
from select_ai.base_profile import BaseProfile, ProfileAttributes
from select_ai.conversation import ConversationAttributes
from select_ai.db import async_cursor, async_get_connection, cursor
from select_ai.errors import ProfileNotFoundError, VectorIndexNotFoundError
from select_ai.provider import Provider
from select_ai.sql import (
    GET_USER_AI_PROFILE_ATTRIBUTES,
    GET_USER_VECTOR_INDEX_ATTRIBUTES,
    LIST_USER_AI_PROFILES,
    LIST_USER_VECTOR_INDEXES_BY_PROFILE,
)
from select_ai.synthetic_data import SyntheticDataAttributes
from select_ai.vector_index import VectorIndex, VectorIndexAttributes

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
        if self.profile_name is not None:
            profile_exists = False
            try:
                saved_attributes = await self.fetch_attributes(
                    profile_name=self.profile_name
                )
                profile_exists = True
            except ProfileNotFoundError:
                if self.attributes is None:
                    raise ValueError("Missing Profile attributes")
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
                await self.create(
                    replace=self.replace, description=self.description
                )
        return self

    @staticmethod
    async def fetch_attributes(profile_name) -> ProfileAttributes:
        """Asynchronously fetch AI profile attributes from the Database

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
        self.attributes = attributes
        parameters = {
            "profile_name": self.profile_name,
            "attributes": self.attributes.json(),
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.SET_ATTRIBUTES", keyword_parameters=parameters
            )

    async def create(
        self, replace: Optional[int] = False, description: Optional[str] = None
    ) -> None:
        """Asynchronously create an AI Profile in the Database

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

        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_PROFILE",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if "already exists" in error.message.lower() and replace:
                    await self.drop(force=True)
                    await cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_PROFILE",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    async def drop(self, force=False) -> None:
        """Asynchronously drop an AI profile from the database

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
    async def from_db(cls, profile_name: str) -> "AsyncProfile":
        """Asynchronously create an AI Profile object from attributes
        saved in the database against the profile

        :param str profile_name:
        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_AI_PROFILE_ATTRIBUTES, profile_name=profile_name
            )
            attributes = await cr.fetchall()
            if attributes:
                attributes = await ProfileAttributes.async_create(
                    **dict(attributes)
                )
                return cls(profile_name=profile_name, attributes=attributes)
            else:
                raise ProfileNotFoundError(profile_name=profile_name)

    @classmethod
    async def list(
        cls, profile_name_pattern: str
    ) -> AsyncGenerator["AsyncProfile", None]:
        """Asynchronously list AI Profiles saved in the database.

        :param str profile_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match

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
                description = row[1]
                attributes = await cls.fetch_attributes(
                    profile_name=profile_name
                )
                yield cls(
                    profile_name=profile_name,
                    description=description,
                    attributes=attributes,
                )

    async def generate(
        self, prompt, action=Action.SHOWSQL, params: Mapping = None
    ) -> Union[pandas.DataFrame, str, None]:
        """Asynchronously perform AI translation using this profile

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

        async with async_cursor() as cr:
            data = await cr.callfunc(
                "DBMS_CLOUD_AI.GENERATE",
                oracledb.DB_TYPE_CLOB,
                keyword_parameters=parameters,
            )
        if data is not None:
            return await data.read()
        return None

    async def chat(self, prompt, params: Mapping = None) -> str:
        """Asynchronously chat with the LLM

        :param str prompt: Natural language prompt
        :param params: Parameters to include in the LLM request
        :return: str
        """
        return await self.generate(prompt, action=Action.CHAT, params=params)

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
        data = await self.generate(prompt, action=Action.RUNSQL, params=params)
        return pandas.DataFrame(json.loads(data))

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

    async def create_vector_index(
        self,
        index_name: str,
        attributes: VectorIndexAttributes,
        description: str = Optional[None],
        replace: Optional[int] = False,
    ) -> None:
        """Create a vector index in the database and populates it with data
        from an object store bucket using an async scheduler job.

        :param str index_name: Name of the vector index
        :param select_ai.VectorIndexAttributes attributes: Attributes of the
         vector index
        :param str description: Description for the vector index
        :param bool replace: True to replace existing vector index

        """

        if attributes.profile_name is None:
            attributes.profile_name = self.profile_name
        parameters = {
            "index_name": index_name,
            "attributes": attributes.json(),
        }
        if description:
            parameters["description"] = description
        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if "already exists" in error.message.lower() and replace:
                    await self.drop_vector_index(
                        force=True, index_name=index_name
                    )
                    await cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

    @staticmethod
    async def drop_vector_index(
        index_name: str,
        include_data: Optional[int] = True,
        force: Optional[int] = False,
    ) -> None:
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
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DROP_VECTOR_INDEX",
                keyword_parameters={
                    "index_name": index_name,
                    "include_data": include_data,
                    "force": force,
                },
            )

    @staticmethod
    async def enable_vector_index(index_name: str) -> None:
        """This procedure enables or activates a previously disabled vector
        index object. Generally, when you create a vector index, by default
        it is enabled such that the AI profile can use it to perform indexing
        and searching.

        :param str index_name: Name of the vector index
        :return: None
        :raises: oracledb.DatabaseError

        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": index_name},
            )

    @staticmethod
    async def disable_vector_index(index_name: str) -> None:
        """This procedure disables a vector index object in the current
        database. When disabled, an AI profile cannot use the vector index,
        and the system does not load data into the vector store as new data
        is added to the object store and does not perform indexing, searching
        or querying based on the index.

        :param str index_name: Name of the vector index
        :return: None
        :raises: oracledb.DatabaseError
        """
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": index_name},
            )

    @staticmethod
    async def update_vector_index(
        index_name: str,
        attribute_name: str,
        attribute_value: Union[str, int],
        attributes: VectorIndexAttributes = None,
    ) -> None:
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute. You can specify a single attribute
        or multiple attributes by passing an object of type
        :class `VectorIndexAttributes`

        :param str index_name: Name of the vector index
        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value
        :param VectorIndexAttributes attributes: Specify multiple attributes
         to update in a single API invocation
        :return: None
        :raises: oracledb.DatabaseError
        """
        if attribute_name and attribute_value and attributes:
            raise ValueError(
                "Only one of attribute (name and value) or "
                "attributes can be specified"
            )
        parameters = {"index_name": index_name}
        if attributes:
            parameters["attributes"] = attributes.json()
        else:
            parameters["attributes_name"] = attribute_name
            parameters["attributes_value"] = attribute_value

        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )

    @staticmethod
    async def fetch_vector_index_attributes(
        index_name: str,
    ) -> VectorIndexAttributes:
        """Fetch attributes of a vector index

        :param str index_name: Name of the vector index
        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_VECTOR_INDEX_ATTRIBUTES, index_name=index_name
            )
            attributes = await cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.AsyncLOB):
                        post_processed_attributes[k] = await v.read()
                    else:
                        post_processed_attributes[k] = v
                return VectorIndexAttributes(**post_processed_attributes)
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    async def list_vector_indexes(
        self, index_name_pattern: str
    ) -> AsyncGenerator[VectorIndex, None]:
        """List Vector Indexes.

        :param str index_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match
        :return: Iterator[VectorIndex]

        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_VECTOR_INDEXES_BY_PROFILE,
                profile_name=self.profile_name,
                index_name_pattern=index_name_pattern,
            )
            rows = await cr.fetchall()
            for row in rows:
                index_name = row[0]
                description = await row[1].read()  # AsyncLOB
                attributes = await AsyncProfile.fetch_vector_index_attributes(
                    index_name=index_name
                )
                yield VectorIndex(
                    index_name=index_name,
                    description=description,
                    attributes=attributes,
                )

    async def generate_synthetic_data(
        self, synthetic_data_attributes: SyntheticDataAttributes
    ) -> None:
        """Generate synthetic data for a single table, multiple tables or a
        full schema.

        :param select_ai.SyntheticDataAttributes synthetic_data_attributes:
        :return: None
        :raises: oracledb.DatabaseError

        """
        keyword_parameters = synthetic_data_attributes.prepare()
        keyword_parameters["profile_name"] = self.profile_name
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.GENERATE_SYNTHETIC_DATA",
                keyword_parameters=keyword_parameters,
            )

    @staticmethod
    async def create_conversation(
        conversation_attributes: ConversationAttributes,
    ) -> str:
        """Creates a new conversation and returns the conversation_id
        to be used in context-aware conversations with LLMs

        :param select_ai.ConversationAttributes conversation_attributes:
         Conversation Attributes

        :return: conversation_id
        """
        async with async_cursor() as cr:
            conversation_id = await cr.callfunc(
                "DBMS_CLOUD_AI.CREATE_CONVERSATION",
                oracledb.DB_TYPE_VARCHAR,
                keyword_parameters={
                    "attributes": conversation_attributes.json()
                },
            )
        return conversation_id

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
                responses.append(await result.return_value.read())
            else:
                responses.append(result.error)
        return responses
