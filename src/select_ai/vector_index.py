import json
from dataclasses import dataclass
from typing import Optional

from select_ai._abc import SelectAIDataClass
from select_ai._enums import StrEnum


@dataclass
class VectorIndex(SelectAIDataClass):
    """
    A Container for VectorIndex

    :param str index_name: The name of the vector index
    :param str description: The description of the vector index
    :param VectorIndexAttributes attributes: The attributes of the vector index
    """

    index_name: str
    description: str
    attributes: "VectorIndexAttributes"


class VectorDBProvider(StrEnum):
    CHROMA = "chroma"
    ORACLE = "oracle"
    PINECONE = "pinecone"
    QDRANT = "qdrant"


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
    vector_db_provider: Optional[VectorDBProvider] = VectorDBProvider.ORACLE
    vector_dimension: Optional[int] = None
    vector_table_name: Optional[str] = None
    pipeline_name: Optional[str] = None

    def json(self, exclude_null=True):
        attributes = self.dict(exclude_null=exclude_null)
        attributes.pop("pipeline_name", None)
        return json.dumps(attributes)
