import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Mapping, Optional

from select_ai._base import SelectAIDataClass


class Provider(StrEnum):
    OPENAI = "openai"
    COHERE = "cohere"
    AZURE = "azure"
    OCI = "oci"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    AWS = "aws"


@dataclass
class ProviderAttributes(SelectAIDataClass):
    """
    Base class for AI Provider attributes

    :param Provider provider: AI service provider

    :param str comments:
    """

    provider: Optional[Provider] = None
    comments: Optional[bool] = None
    conversation: Optional[str] = None
    credential_name: Optional[str] = None
    embedding_model: Optional[str] = None
    max_tokens: Optional[int] = 1024
    model: Optional[str] = None
    object_list: Optional[List[Mapping]] = None
    region: Optional[str] = None
    stop_tokens: Optional[str] = None
    temperature: Optional[float] = None
    vector_index_name: Optional[str] = None
    provider_endpoint: Optional[str] = None
    annotations: Optional[str] = None
    constraints: Optional[str] = None
    case_sensitive_values: Optional[bool] = None
    object_list_mode: Optional[bool] = None
    enforce_object_list: Optional[bool] = None
    enable_sources: Optional[bool] = None
    enable_source_offsets: Optional[bool] = None
    seed: Optional[str] = None
    streaming: Optional[str] = None

    def dict(self, filter_null=False):
        attributes = {}
        for k, v in self.__dict__.items():
            if (not v and not filter_null) or v:
                attributes[k] = v
        return attributes

    def json(self, filter_null=True):
        attributes = self.dict(filter_null=filter_null)
        return json.dumps(attributes)

    @classmethod
    def create(cls, *, provider: Optional[Provider] = None, **kwargs):
        for subclass in cls.__subclasses__():
            if subclass.provider == provider:
                return subclass(**kwargs)
        return cls(**kwargs)


@dataclass
class AzureAIProviderAttributes(ProviderAttributes):
    """
    Azure specific attributes
    """

    provider: Provider = Provider.AZURE
    azure_deployment_name: Optional[str] = None
    azure_embedding_deployment_name: Optional[str] = None
    azure_resource_name: Optional[str] = None

    def __post_init__(self):
        self.provider_endpoint = f"{self.azure_resource_name}.openai.azure.com"


@dataclass
class OpenAIProviderAttributes(ProviderAttributes):
    """
    OpenAI specific attributes
    """

    provider: Provider = Provider.OPENAI
    provider_endpoint: Optional[str] = "api.openai.com"


@dataclass
class OCIGenAIProviderAttributes(ProviderAttributes):
    """
    OCI Gen AI specific attributes
    """

    provider: Provider = Provider.OCI
    oci_apiformat: Optional[str] = None
    oci_compartment_id: Optional[str] = None
    oci_endpoint_id: Optional[str] = None
    oci_runtimetype: Optional[str] = None


@dataclass
class CohereAIProviderAttributes(ProviderAttributes):
    """
    Cohere AI specific attributes
    """

    provider: Provider = Provider.COHERE
    provider_endpoint = "api.cohere.ai"


@dataclass
class GoogleAIProviderAttributes(ProviderAttributes):
    """
    Google AI specific attributes
    """

    provider: Provider = Provider.GOOGLE
    provider_endpoint = "generativelanguage.googleapis.com"


@dataclass
class HuggingFaceAIProviderAttributes(ProviderAttributes):
    """
    HuggingFace specific attributes
    """

    provider: Provider = Provider.HUGGINGFACE
    provider_endpoint = "api-inference.huggingface.co"


@dataclass
class AWSAIProviderAttributes(ProviderAttributes):
    """
    AWS specific attributes
    """

    provider: Provider = Provider.AWS
    provider_endpoint = "api-inference.huggingface.co"
    aws_apiformat: Optional[str] = None


@dataclass
class AnthropicAIProviderAttributes(ProviderAttributes):
    """
    Anthropic specific attributes
    """

    provider: Provider = Provider.ANTHROPIC
    provider_endpoint = "api.anthropic.com"
