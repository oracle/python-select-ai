import json
from dataclasses import dataclass
from typing import NamedTuple, Optional

from select_ai._base import SelectAIDataClass
from select_ai._enums import StrEnum


class VectorIndex(NamedTuple):
    """
    A Container for VectorIndex
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

    def json(self):
        attributes = {}
        for k, v in self.__dict__.items():
            if v:
                attributes[k] = v
        # ORA-20048: pipeline_name cannot be set or modified
        # for the vector index
        attributes.pop("pipeline_name", None)
        return json.dumps(attributes)
