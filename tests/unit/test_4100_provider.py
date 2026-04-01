# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import pytest

from select_ai.provider import (
    ANTHROPIC,
    AWS,
    AZURE,
    COHERE,
    GOOGLE,
    HUGGINGFACE,
    OCI,
    OPENAI,
    AWSProvider,
    AnthropicProvider,
    AzureProvider,
    CohereProvider,
    GoogleProvider,
    HuggingFaceProvider,
    OCIGenAIProvider,
    OpenAIProvider,
    Provider,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        (OPENAI, OpenAIProvider),
        (AZURE, AzureProvider),
        (OCI, OCIGenAIProvider),
        (COHERE, CohereProvider),
        (GOOGLE, GoogleProvider),
        (HUGGINGFACE, HuggingFaceProvider),
        (AWS, AWSProvider),
        (ANTHROPIC, AnthropicProvider),
    ],
)
def test_4100_create_returns_expected_provider_subclass(
    provider_name, expected_type
):
    provider = Provider.create(provider_name=provider_name)
    assert isinstance(provider, expected_type)


def test_4101_create_falls_back_to_base_provider_for_unknown_name():
    provider = Provider.create(provider_name="custom")
    assert type(provider) is Provider


def test_4102_key_alias_maps_provider_fields():
    assert Provider.key_alias("provider") == "provider_name"
    assert Provider.key_alias("provider_name") == "provider"
    assert Provider.key_alias("model") == "model"


def test_4103_keys_contains_provider_specific_fields():
    keys = Provider.keys()
    assert "provider" in keys
    assert "provider_endpoint" in keys
    assert "azure_resource_name" in keys
    assert "oci_compartment_id" in keys
    assert "aws_apiformat" in keys


def test_4104_azure_provider_sets_endpoint_from_resource_name():
    provider = AzureProvider(azure_resource_name="demo-resource")
    assert provider.provider_endpoint == "demo-resource.openai.azure.com"


def test_4105_aws_provider_sets_endpoint_from_region():
    provider = AWSProvider(region="us-phoenix-1")
    assert provider.provider_endpoint == "bedrock-runtime.us-phoenix-1.amazonaws.com"


def test_4106_default_provider_endpoints_are_exposed():
    assert OpenAIProvider().provider_endpoint == "api.openai.com"
    assert CohereProvider.provider_endpoint == "api.cohere.ai"
    assert GoogleProvider.provider_endpoint == "generativelanguage.googleapis.com"
    assert HuggingFaceProvider.provider_endpoint == "api-inference.huggingface.co"
    assert AnthropicProvider.provider_endpoint == "api.anthropic.com"
