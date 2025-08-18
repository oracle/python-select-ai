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
from select_ai.errors import VectorIndexNotFoundError
from select_ai.profile import Profile
from select_ai.sql import (
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

    chunk_size: Optional[int] = 1024
    chunk_overlap: Optional[int] = 128
    location: Optional[str] = None
    match_limit: Optional[int] = 5
    object_storage_credential_name: Optional[str] = None
    profile_name: Optional[str] = None
    refresh_rate: Optional[int] = 1440
    similarity_threshold: Optional[float] = 0
    vector_distance_metric: Optional[VectorDistanceMetric] = (
        VectorDistanceMetric.COSINE
    )
    vector_db_endpoint: Optional[str] = None
    vector_db_credential_name: Optional[str] = None
    vector_db_provider: Optional[VectorDBProvider] = None
    vector_dimension: Optional[int] = None
    vector_table_name: Optional[str] = None
    pipeline_name: Optional[str] = None

    def json(self, exclude_null=True):
        attributes = self.dict(exclude_null=exclude_null)
        attributes.pop("pipeline_name", None)
        return json.dumps(attributes)

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
        profile: BaseProfile = None,
        index_name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[VectorIndexAttributes] = None,
    ):
        """Initialize a Vector Index"""
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
                return VectorIndexAttributes.create(
                    **post_processed_attributes
                )
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
            cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": self.index_name},
            )

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
            cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": self.index_name},
            )

    def set_attributes(
        self,
        attribute_name: str,
        attribute_value: Union[str, int, float],
        attributes: VectorIndexAttributes = None,
    ):
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute. You can specify a single attribute
        or multiple attributes by passing an object of type
        :class `VectorIndexAttributes`

        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value
        :param VectorIndexAttributes attributes: Specify multiple attributes
         to update in a single API invocation
        :return: None
        :raises: oracledb.DatabaseError
        """
        if attribute_name and attribute_value and attributes:
            raise ValueError(
                "Either specify a single attribute using "
                "attribute_name and attribute_value or "
                "pass an object of type VectorIndexAttributes"
            )

        parameters = {"index_name": self.index_name}
        if attributes:
            parameters["attributes"] = attributes.json()
            self.attributes = attributes
        else:
            setattr(self.attributes, attribute_name, attribute_value)
            parameters["attributes_name"] = attribute_name
            parameters["attributes_value"] = attribute_value

        with cursor() as cr:
            cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )

    def get_attributes(self) -> VectorIndexAttributes:
        """Get attributes of this vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        return self._get_attributes(self.index_name)

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
                if row[1]:
                    description = row[1].read()  # Oracle.LOB
                else:
                    description = None
                attributes = cls._get_attributes(index_name=index_name)
                yield cls(
                    index_name=index_name,
                    description=description,
                    attributes=attributes,
                    profile=Profile(profile_name=attributes.profile_name),
                )


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
                return VectorIndexAttributes.create(
                    **post_processed_attributes
                )
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
            await cr.callproc(
                "DBMS_CLOUD_AI.ENABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": self.index_name},
            )

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
            await cr.callproc(
                "DBMS_CLOUD_AI.DISABLE_VECTOR_INDEX",
                keyword_parameters={"index_name": self.index_name},
            )

    async def set_attributes(
        self,
        attribute_name: str,
        attribute_value: Union[str, int],
        attributes: VectorIndexAttributes = None,
    ) -> None:
        """
        This procedure updates an existing vector store index with a specified
        value of the vector index attribute. You can specify a single attribute
        or multiple attributes by passing an object of type
        :class `VectorIndexAttributes`

        :param str attribute_name: Custom attribute name
        :param Union[str, int, float] attribute_value: Attribute Value
        :param VectorIndexAttributes attributes: Specify multiple attributes
         to update in a single API invocation
        :return: None
        :raises: oracledb.DatabaseError
        """
        if attribute_name and attribute_value and attributes:
            raise ValueError(
                "Either specify a single attribute using "
                "attribute_name and attribute_value or "
                "pass an object of type VectorIndexAttributes"
            )
        parameters = {"index_name": self.index_name}
        if attributes:
            self.attributes = attributes
            parameters["attributes"] = attributes.json()
        else:
            setattr(self.attributes, attribute_name, attribute_value)
            parameters["attributes_name"] = attribute_name
            parameters["attributes_value"] = attribute_value

        async with async_cursor() as cr:
            await cr.callproc(
                "DBMS_CLOUD_AI.UPDATE_VECTOR_INDEX",
                keyword_parameters=parameters,
            )

    async def get_attributes(self) -> VectorIndexAttributes:
        """Get attributes of a vector index

        :return: select_ai.VectorIndexAttributes
        :raises: VectorIndexNotFoundError
        """
        return await self._get_attributes(index_name=self.index_name)

    @classmethod
    async def list(
        cls, index_name_pattern: str = ".*"
    ) -> AsyncGenerator[VectorIndex, None]:
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
                if row[1]:
                    description = await row[1].read()  # AsyncLOB
                else:
                    description = None
                attributes = await cls._get_attributes(index_name=index_name)
                yield VectorIndex(
                    index_name=index_name,
                    description=description,
                    attributes=attributes,
                    profile=await AsyncProfile(
                        profile_name=attributes.profile_name
                    ),
                )
