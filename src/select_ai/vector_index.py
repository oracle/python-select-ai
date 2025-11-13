# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from abc import ABC
from dataclasses import dataclass
from typing import AsyncGenerator, Iterator, Optional, Union

import oracledb

from select_ai import BaseProfile
from select_ai._abc import SelectAIDataClass
from select_ai._enums import StrEnum
from select_ai.async_profile import AsyncProfile
from select_ai.db import async_cursor, cursor
from select_ai.errors import ProfileNotFoundError, VectorIndexNotFoundError
from select_ai.profile import Profile
from select_ai.sql import (
    GET_USER_VECTOR_INDEX,
    GET_USER_VECTOR_INDEX_ATTRIBUTES,
    LIST_USER_VECTOR_INDEXES,
)


class VectorDBProvider(StrEnum):
    ORACLE = "oracle"


class VectorDistanceMetric(StrEnum):
    EUCLIDEAN = "EUCLIDEAN"
    L2_SQUARED = "L2_SQUARED"
    COSINE = "COSINE"
    DOT = "DOT"
    MANHATTAN = "MANHATTAN"
    HAMMING = "HAMMING"


@dataclass
class VectorIndexAttributes(SelectAIDataClass):
    """
    Attributes of a vector index help to manage and configure the behavior of
    the vector index.

    :param int chunk_size: Text size of chunking the input data.
    :param int chunk_overlap: Specifies the amount of overlapping
     characters between adjacent chunks of text.
    :param str location: Location of the object store.
    :param int match_limit: Specifies the maximum number of results to return
     in a vector search query
    :param str object_storage_credential_name: Name of the credentials for
     accessing object storage.
    :param str profile_name: Name of the AI profile which is used for
     embedding source data and user prompts.
    :param int refresh_rate: Interval of updating data in the vector store.
     The unit is minutes.
    :param float similarity_threshold: Defines the minimum level of similarity
     required for two items to be considered a match
    :param VectorDistanceMetric vector_distance_metric: Specifies the type of
     distance calculation used to compare vectors in a database
    :param VectorDBProvider vector_db_provider: Name of the Vector database
     provider. Default value is "oracle"
    :param str  vector_db_endpoint: Endpoint to access the Vector database
    :param str vector_db_credential_name: Name of the credentials for accessing
     Vector database
    :param int vector_dimension: Specifies the number of elements in each
     vector within the vector store
    :param str vector_table_name: Specifies the name of the table or collection
     to store vector embeddings and chunked data
    """

    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    location: Optional[str] = None
    match_limit: Optional[int] = None
    object_storage_credential_name: Optional[str] = None
    profile_name: Optional[str] = None
    refresh_rate: Optional[int] = None
    similarity_threshold: Optional[float] = None
    vector_distance_metric: Optional[VectorDistanceMetric] = None
    vector_db_endpoint: Optional[str] = None
    vector_db_credential_name: Optional[str] = None
    vector_db_provider: Optional[VectorDBProvider] = None
    vector_dimension: Optional[int] = None
    vector_table_name: Optional[str] = None
    pipeline_name: Optional[str] = None

    @classmethod
    def create(cls, *, vector_db_provider: Optional[str] = None, **kwargs):
        for subclass in cls.__subclasses__():
            if subclass.vector_db_provider == vector_db_provider:
                return subclass(**kwargs)
        return cls(**kwargs)


@dataclass
class OracleVectorIndexAttributes(VectorIndexAttributes):
    """Oracle specific vector index attributes"""

    vector_db_provider: Optional[VectorDBProvider] = VectorDBProvider.ORACLE


class _BaseVectorIndex(ABC):

    def __init__(
        self,
        profile: Optional[BaseProfile] = None,
        index_name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[VectorIndexAttributes] = None,
    ):
        """Initialize a Vector Index"""
        if attributes and not isinstance(attributes, VectorIndexAttributes):
            raise TypeError(
                "'attributes' must be an object of type "
                "select_ai.VectorIndexAttributes"
            )
        if profile and not isinstance(profile, BaseProfile):
            raise TypeError(
                "'profile' must be an object of type "
                "select_ai.Profile or select_ai.AsyncProfile"
            )
        self.profile = profile
        self.index_name = index_name
        self.attributes = attributes
        self.description = description

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(profile={self.profile}, "
            f"index_name={self.index_name}, "
            f"attributes={self.attributes}, description={self.description})"
        )


class VectorIndex(_BaseVectorIndex):
    """
    VectorIndex objects let you manage vector indexes

    :param str index_name: The name of the vector index
    :param str description: The description of the vector index
    :param select_ai.VectorIndexAttributes attributes: The attributes of the vector index
    """

    @staticmethod
    def _get_attributes(index_name: str) -> VectorIndexAttributes:
        """Get attributes of a vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        if not index_name:
            raise AttributeError("'index_name' is required")
        with cursor() as cr:
            cr.execute(
                GET_USER_VECTOR_INDEX_ATTRIBUTES, index_name=index_name.upper()
            )
            attributes = cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.LOB):
                        post_processed_attributes[k] = v.read()
                    else:
                        post_processed_attributes[k] = v
                return VectorIndexAttributes.create(
                    **post_processed_attributes
                )
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    @staticmethod
    def _get_description(index_name) -> Union[str, None]:
        """Get description of the Vector Index from USER_CLOUD_VECTOR_INDEXES

        :param str index_name: The name of the vector index
        :return: Union[str, None] profile description
        :raises: ProfileNotFoundError
        """
        if not index_name:
            raise AttributeError("'index_name' is required")
        with cursor() as cr:
            cr.execute(GET_USER_VECTOR_INDEX, index_name=index_name.upper())
            index = cr.fetchone()
            if index:
                if index[1] is not None:
                    return index[1].read()
                else:
                    return None
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    def create(self, replace: Optional[bool] = False):
        """Create a vector index in the database and populates the index
         with data from an object store bucket using an async scheduler job

        :param bool replace: Replace vector index if it exists
        :return: None
        """

        if self.attributes.profile_name is None:
            self.attributes.profile_name = self.profile.profile_name

        parameters = {
            "index_name": self.index_name,
            "attributes": self.attributes.json(),
        }

        if self.description:
            parameters["description"] = self.description

        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if error.code == 20048 and replace:
                    self.delete(force=True)
                    cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                        keyword_parameters=parameters,
                    )
                else:
                    raise
        self.profile.set_attribute("vector_index_name", self.index_name)

    def delete(
        self,
        include_data: Optional[bool] = True,
        force: Optional[bool] = False,
    ):
        """This procedure removes a vector store index

        :param bool include_data: Indicates whether to delete
         both the customer's vector store and vector index
         along with the vector index object
        :param bool force: Indicates whether to ignore errors
         that occur if the vector index does not exist
        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.DROP_VECTOR_INDEX",
                keyword_parameters={
                    "index_name": self.index_name,
                    "include_data": include_data,
                    "force": force,
                },
            )

    def enable(self):
        """This procedure enables or activates a previously disabled vector
        index object. Generally, when you create a vector index, by default
        it is enabled such that the AI profile can use it to perform indexing
        and searching.

        :return: None
        :raises: oracledb.DatabaseError

        """
        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                    keyword_parameters={"index_name": self.index_name},
                )
            except oracledb.Error as e:
                (error,) = e.args
                # ORA-20000: Vector Index is already in the desired status
                if error.code == 20000:
                    pass
                else:
                    raise

    def disable(self):
        """This procedure disables a vector index object in the current
        database. When disabled, an AI profile cannot use the vector index,
        and the system does not load data into the vector store as new data
        is added to the object store and does not perform indexing, searching
        or querying based on the index.

        :return: None
        :raises: oracledb.DatabaseError
        """
        with cursor() as cr:
            try:
                cr.callproc(
                    "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                    keyword_parameters={"index_name": self.index_name},
                )
            except oracledb.Error as e:
                (error,) = e.args
                # ORA-20000: Vector Index is already in the desired status
                if error.code == 20000:
                    pass
                else:
                    raise

    @classmethod
    def fetch(cls, index_name: str) -> "VectorIndex":
        """
        Fetches vector index attributes from the
        database and builds a proxy object for the
        passed index_name

        :param str index_name: The name of the vector index
        """
        description = cls._get_description(index_name)
        attributes = cls._get_attributes(index_name)
        try:
            profile = Profile(profile_name=attributes.profile_name)
        except ProfileNotFoundError:
            profile = None
        return cls(
            description=description,
            attributes=attributes,
            profile=profile,
            index_name=index_name,
        )

    def set_attribute(
        self,
        attribute_name: str,
        attribute_value: Union[str, int, float],
    ):
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute.

        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value

        """
        setattr(self.attributes, attribute_name, attribute_value)
        parameters = {
            "index_name": self.index_name,
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )

    def set_attributes(
        self,
        attributes: VectorIndexAttributes = None,
    ):
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attributes. Specify multiple attributes by
        passing an object of type :class `VectorIndexAttributes`

        :param select_ai.VectorIndexAttributes attributes: Use this to
         update multiple attribute values
        :return: None
        :raises: oracledb.DatabaseError
        """
        parameters = {
            "index_name": self.index_name,
            "attributes": attributes.json(),
        }
        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )
        self.attributes = self.get_attributes()

    def get_attributes(self) -> VectorIndexAttributes:
        """Get attributes of this vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        return self._get_attributes(self.index_name)

    def get_profile(self) -> Profile:
        """Get Profile object linked to this vector index

        :return: select_ai.Profile
        :raises: ProfileNotFoundError
        """
        attributes = self._get_attributes(index_name=self.index_name)
        profile = Profile(profile_name=attributes.profile_name)
        return profile

    @classmethod
    def list(cls, index_name_pattern: str = ".*") -> Iterator["VectorIndex"]:
        """List Vector Indexes

        :param str index_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all vector indexes.

        :return: Iterator[VectorIndex]
        """
        with cursor() as cr:
            cr.execute(
                LIST_USER_VECTOR_INDEXES,
                index_name_pattern=index_name_pattern,
            )
            for row in cr.fetchall():
                index_name = row[0]
                yield cls.fetch(index_name=index_name)


class AsyncVectorIndex(_BaseVectorIndex):
    """
    AsyncVectorIndex objects let you manage vector indexes
    using async APIs. Use this for non-blocking concurrent
    requests

    :param str index_name: The name of the vector index
    :param str description: The description of the vector index
    :param VectorIndexAttributes attributes: The attributes of the vector index
    """

    @staticmethod
    async def _get_attributes(index_name: str) -> VectorIndexAttributes:
        """Get attributes of a vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        if not index_name:
            raise AttributeError("'index_name' is required")
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_VECTOR_INDEX_ATTRIBUTES, index_name=index_name.upper()
            )
            attributes = await cr.fetchall()
            if attributes:
                post_processed_attributes = {}
                for k, v in attributes:
                    if isinstance(v, oracledb.AsyncLOB):
                        post_processed_attributes[k] = await v.read()
                    else:
                        post_processed_attributes[k] = v
                return VectorIndexAttributes.create(
                    **post_processed_attributes
                )
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    @staticmethod
    async def _get_description(index_name) -> Union[str, None]:
        """Get description of the Vector Index from USER_CLOUD_VECTOR_INDEXES

        :param str index_name: The name of the vector index
        :return: Union[str, None] profile description
        :raises: ProfileNotFoundError
        """
        if not index_name:
            raise AttributeError("'index_name' is required")
        async with async_cursor() as cr:
            await cr.execute(
                GET_USER_VECTOR_INDEX, index_name=index_name.upper()
            )
            index = await cr.fetchone()
            if index:
                if index[1] is not None:
                    return await index[1].read()
                else:
                    return None
            else:
                raise VectorIndexNotFoundError(index_name=index_name)

    async def create(self, replace: Optional[bool] = False) -> None:
        """Create a vector index in the database and populates it with data
        from an object store bucket using an async scheduler job

        :param bool replace: True to replace existing vector index

        """

        if self.attributes.profile_name is None:
            self.attributes.profile_name = self.profile.profile_name
        parameters = {
            "index_name": self.index_name,
            "attributes": self.attributes.json(),
        }
        if self.description:
            parameters["description"] = self.description
        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                    keyword_parameters=parameters,
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # If already exists and replace is True then drop and recreate
                if error.code == 20048 and replace:
                    await self.delete(force=True)
                    await cr.callproc(
                        "DBMS_CLOUD_AI.CREATE_VECTOR_INDEX",
                        keyword_parameters=parameters,
                    )
                else:
                    raise

        await self.profile.set_attribute("vector_index_name", self.index_name)

    async def delete(
        self,
        include_data: Optional[bool] = True,
        force: Optional[bool] = False,
    ) -> None:
        """This procedure removes a vector store index.

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
                    "index_name": self.index_name,
                    "include_data": include_data,
                    "force": force,
                },
            )

    async def enable(self) -> None:
        """This procedure enables or activates a previously disabled vector
        index object. Generally, when you create a vector index, by default
        it is enabled such that the AI profile can use it to perform indexing
        and searching.

        :return: None
        :raises: oracledb.DatabaseError

        """
        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                    keyword_parameters={"index_name": self.index_name},
                )
            except oracledb.DatabaseError as e:
                (error,) = e.args
                # ORA-20000: Vector Index is already in the desired status
                if error.code == 20000:
                    pass
                else:
                    raise

    async def disable(self) -> None:
        """This procedure disables a vector index object in the current
        database. When disabled, an AI profile cannot use the vector index,
        and the system does not load data into the vector store as new data
        is added to the object store and does not perform indexing, searching
        or querying based on the index.

        :return: None
        :raises: oracledb.DatabaseError
        """
        async with async_cursor() as cr:
            try:
                await cr.callproc(
                    "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                    keyword_parameters={"index_name": self.index_name},
                )
            except oracledb.Error as e:
                (error,) = e.args
                if error.code == 20000:
                    pass
                else:
                    raise

    @classmethod
    async def fetch(cls, index_name: str) -> "AsyncVectorIndex":
        """
        Fetches vector index attributes from the
        database and builds a proxy object for the
        passed index_name

        :param str index_name: The name of the vector index
        """
        description = await cls._get_description(index_name)
        attributes = await cls._get_attributes(index_name)
        try:
            profile = await AsyncProfile(profile_name=attributes.profile_name)
        except ProfileNotFoundError:
            profile = None
        return cls(
            description=description,
            attributes=attributes,
            profile=profile,
            index_name=index_name,
        )

    async def set_attribute(
        self, attribute_name: str, attribute_value: Union[str, int, float]
    ) -> None:
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute.

        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value

        """
        parameters = {
            "index_name": self.index_name,
            "attribute_name": attribute_name,
            "attribute_value": attribute_value,
        }
        setattr(self.attributes, attribute_name, attribute_value)
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )

    async def set_attributes(self, attributes: VectorIndexAttributes) -> None:
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute. multiple attributes by passing
        an object of type :class `VectorIndexAttributes`

        :param select_ai.VectorIndexAttributes attributes: Use this to
         update multiple attribute values
        :return: None
        :raises: oracledb.DatabaseError
        """
        parameters = {
            "index_name": self.index_name,
            "attributes": attributes.json(),
        }
        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )
        self.attributes = await self.get_attributes()

    async def get_attributes(self) -> VectorIndexAttributes:
        """Get attributes of a vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        return await self._get_attributes(index_name=self.index_name)

    async def get_profile(self) -> AsyncProfile:
        """Get AsyncProfile object linked to this vector index

        :return: select_ai.AsyncProfile
        :raises: ProfileNotFoundError
        """
        attributes = await self._get_attributes(index_name=self.index_name)
        profile = await AsyncProfile(profile_name=attributes.profile_name)
        return profile

    @classmethod
    async def list(
        cls, index_name_pattern: str = ".*"
    ) -> AsyncGenerator["AsyncVectorIndex", None]:
        """List Vector Indexes.

        :param str index_name_pattern: Regular expressions can be used
         to specify a pattern. Function REGEXP_LIKE is used to perform the
         match. Default value is ".*" i.e. match all vector indexes.

        :return: AsyncGenerator[VectorIndex]

        """
        async with async_cursor() as cr:
            await cr.execute(
                LIST_USER_VECTOR_INDEXES,
                index_name_pattern=index_name_pattern,
            )
            rows = await cr.fetchall()
            for row in rows:
                index_name = row[0]
                index = await cls.fetch(index_name=index_name)
                yield index
