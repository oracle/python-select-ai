# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from typing import List, Optional, Union

from select_ai._abc import SelectAIDataClass
from select_ai._validations import enforce_types

from .db import async_cursor, cursor
from .sql import (
    DISABLE_AI_PROFILE_DOMAIN_FOR_USER,
    ENABLE_AI_PROFILE_DOMAIN_FOR_USER,
    GRANT_PRIVILEGES_TO_USER,
    REVOKE_PRIVILEGES_FROM_USER,
)

OPENAI = "openai"
COHERE = "cohere"
AZURE = "azure"
OCI = "oci"
GOOGLE = "google"
ANTHROPIC = "anthropic"
HUGGINGFACE = "huggingface"
AWS = "aws"


@dataclass
class Provider(SelectAIDataClass):
    """
    Base class for AI Provider

    To create an object of Provider class, use any one of the concrete AI
    provider implementations

    :param str embedding_model: The embedding model, also known as a
     transformer. Depending on the AI provider, the supported embedding models
     vary
    :param str model: The name of the LLM being used to generate
     responses
    :param str provider_name: The name of the provider being used
    :param str provider_endpoint: Endpoint URL of the AI provider being used
    :param str region: The cloud region of the Gen AI cluster

    """

    embedding_model: Optional[str] = None
    model: Optional[str] = None
    provider_name: Optional[str] = None
    provider_endpoint: Optional[str] = None
    region: Optional[str] = None

    @classmethod
    def create(cls, *, provider_name: Optional[str] = None, **kwargs):
        for subclass in cls.__subclasses__():
            if subclass.provider_name == provider_name:
                return subclass(**kwargs)
        return cls(**kwargs)

    @classmethod
    def key_alias(cls, k):
        return {"provider": "provider_name", "provider_name": "provider"}.get(
            k, k
        )

    @classmethod
    def keys(cls):
        return {
            "provider",
            "provider_name",
            "embedding_model",
            "model",
            "region",
            "provider_endpoint",
            "azure_deployment_name",
            "azure_embedding_deployment_name",
            "azure_resource_name",
            "oci_apiformat",
            "oci_compartment_id",
            "oci_endpoint_id",
            "oci_runtimetype",
            "aws_apiformat",
        }


@dataclass
class AzureProvider(Provider):
    """
    Azure specific attributes

    :param str azure_deployment_name: Name of the Azure OpenAI Service
     deployed model.
    :param str azure_embedding_deployment_name: Name of the Azure OpenAI
     deployed embedding model.
    :param str azure_resource_name: Name of the Azure OpenAI Service resource
    """

    provider_name: str = AZURE
    azure_deployment_name: Optional[str] = None
    azure_embedding_deployment_name: Optional[str] = None
    azure_resource_name: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.provider_endpoint = f"{self.azure_resource_name}.openai.azure.com"


@dataclass
class OpenAIProvider(Provider):
    """
    OpenAI specific attributes
    """

    provider_name: str = OPENAI
    provider_endpoint: Optional[str] = "api.openai.com"


@dataclass
class OCIGenAIProvider(Provider):
    """
    OCI Gen AI specific attributes

    :param str oci_apiformat: Specifies the format in which the API expects
     data to be sent and received. Supported values are 'COHERE' and 'GENERIC'
    :param str oci_compartment_id: Specifies the OCID of the compartment you
     are permitted to access when calling the OCI Generative AI service
    :param str oci_endpoint_id: This attributes indicates the endpoint OCID
     of the Oracle dedicated AI hosting cluster
    :param str oci_runtimetype: This attribute indicates the runtime type of
     the provided model. The supported values are 'COHERE' and 'LLAMA'
    """

    provider_name: str = OCI
    oci_apiformat: Optional[str] = None
    oci_compartment_id: Optional[str] = None
    oci_endpoint_id: Optional[str] = None
    oci_runtimetype: Optional[str] = None


@dataclass
class CohereProvider(Provider):
    """
    Cohere AI specific attributes
    """

    provider_name: str = COHERE
    provider_endpoint = "api.cohere.ai"


@dataclass
class GoogleProvider(Provider):
    """
    Google AI specific attributes
    """

    provider_name: str = GOOGLE
    provider_endpoint = "generativelanguage.googleapis.com"


@dataclass
class HuggingFaceProvider(Provider):
    """
    HuggingFace specific attributes
    """

    provider_name: str = HUGGINGFACE
    provider_endpoint = "api-inference.huggingface.co"


@dataclass
class AWSProvider(Provider):
    """
    AWS specific attributes
    """

    provider_name: str = AWS
    aws_apiformat: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.provider_endpoint = f"bedrock-runtime.{self.region}.amazonaws.com"


@dataclass
class AnthropicProvider(Provider):
    """
    Anthropic specific attributes
    """

    provider_name: str = ANTHROPIC
    provider_endpoint = "api.anthropic.com"
