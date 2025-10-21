# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1300 - Module for testing the AsyncProfile proxy object
"""

import oracledb
import pytest
import select_ai
from select_ai import AsyncProfile, ProfileAttributes


@pytest.fixture(scope="module")
def provider():
    return select_ai.OCIGenAIProvider(
        region="us-phoenix-1", oci_apiformat="GENERIC"
    )


@pytest.fixture(scope="module")
def profile_attributes(provider, oci_credential):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[{"owner": "SH"}],
        provider=provider,
    )


@pytest.fixture(scope="module")
def min_profile_attributes(provider, oci_credential):
    return ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=select_ai.OCIGenAIProvider(),
    )


@pytest.fixture(scope="module")
async def python_gen_ai_profile(profile_attributes):
    profile = await AsyncProfile(
        profile_name="PYTHON_GENAI_PROFILE",
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_profile_2(profile_attributes):
    profile = await AsyncProfile(
        profile_name="PYTHON_GENAI_PROFILE_2",
        description="OCI GENAI Profile 2",
        attributes=profile_attributes,
    )
    await profile.create(replace=True)
    yield profile
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_min_attr_profile(min_profile_attributes):
    profile = await AsyncProfile(
        profile_name="PYTHON_MIN_ATTRIB_PROFILE",
        attributes=min_profile_attributes,
        description=None,
    )
    yield profile
    await profile.delete(force=True)


@pytest.fixture
async def python_gen_ai_duplicate_profile(min_profile_attributes):
    profile = await AsyncProfile(
        profile_name="PYTHON_DUPLICATE_PROFILE",
        attributes=min_profile_attributes,
    )
    yield profile
    await profile.delete(force=True)


def test_1300(python_gen_ai_profile, profile_attributes):
    """Create basic Profile"""
    assert python_gen_ai_profile.profile_name == "PYTHON_GENAI_PROFILE"
    assert python_gen_ai_profile.attributes == profile_attributes
    assert python_gen_ai_profile.description == "OCI GENAI Profile"


def test_1301(python_gen_ai_profile_2, profile_attributes):
    """Create Profile using create method"""
    assert python_gen_ai_profile_2.profile_name == "PYTHON_GENAI_PROFILE_2"
    assert python_gen_ai_profile_2.attributes == profile_attributes
    assert python_gen_ai_profile_2.description == "OCI GENAI Profile 2"


async def test_1302(profile_attributes):
    """Create duplicate profile with replace=True"""
    duplicate = await AsyncProfile(
        profile_name="PYTHON_GENAI_PROFILE",
        attributes=profile_attributes,
        replace=True,
    )
    assert duplicate.profile_name == "PYTHON_GENAI_PROFILE"
    assert duplicate.attributes == profile_attributes
    assert duplicate.description is None


def test_1303(python_gen_ai_min_attr_profile, min_profile_attributes):
    """Create Profile with minimum required attributes"""
    assert (
        python_gen_ai_min_attr_profile.profile_name
        == "PYTHON_MIN_ATTRIB_PROFILE"
    )
    assert python_gen_ai_min_attr_profile.attributes == min_profile_attributes
    assert python_gen_ai_min_attr_profile.description is None


async def test_1304():
    """List profiles without regex"""
    profile_list = [
        profile.profile_name async for profile in AsyncProfile.list()
    ]
    assert len(profile_list) == 3


async def test_1305():
    """List profiles with regex"""
    profile_list = [
        profile
        async for profile in AsyncProfile.list(
            profile_name_pattern=".*PROFILE$"
        )
    ]
    assert len(profile_list) == 2


async def test_1306(profile_attributes):
    """Get attributes for a Profile"""
    profile = await AsyncProfile("PYTHON_GENAI_PROFILE")
    fetched_attributes = await profile.get_attributes()
    assert fetched_attributes == profile_attributes


async def test_1307():
    """Set attributes for a Profile"""
    profile = await AsyncProfile("PYTHON_GENAI_PROFILE")
    assert profile.attributes.provider.model is None
    await profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    assert profile.attributes.provider.model == "meta.llama-3.1-70b-instruct"


async def test_1308(oci_credential):
    """Set multiple attributes for a Profile"""
    profile = AsyncProfile("PYTHON_GENAI_PROFILE")
    profile_attrs = ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=select_ai.OCIGenAIProvider(),
        object_list=[{"owner": "ADMIN", "name": "gymnasts"}],
        comments=True,
    )
    await profile.set_attributes(profile_attrs)
    assert profile.attributes.object_list == [
        {"owner": "ADMIN", "name": "gymnasts"}
    ]
    assert profile.attributes.comments is True
    fetched_attributes = await profile.get_attributes()
    assert fetched_attributes == profile_attrs


async def test_1309(python_gen_ai_duplicate_profile):
    """Create duplicate profile without replace"""
    # expected - ProfileExistsError
    with pytest.raises(select_ai.errors.ProfileExistsError):
        await AsyncProfile(
            profile_name=python_gen_ai_duplicate_profile.profile_name,
            attributes=python_gen_ai_duplicate_profile.attributes,
        )


async def test_1310(python_gen_ai_duplicate_profile):
    """Create duplicate profile with replace=False"""
    # expected - select_ai.ProfileExistsError
    with pytest.raises(select_ai.errors.ProfileExistsError):
        await AsyncProfile(
            profile_name=python_gen_ai_duplicate_profile.profile_name,
            attributes=python_gen_ai_duplicate_profile.attributes,
            replace=False,
        )


@pytest.mark.parametrize(
    "invalid_provider",
    [
        "openai",
        {"region": "us-ashburn"},
        object(),
    ],
)
async def test_1311(invalid_provider):
    """Create Profile with invalid providers"""
    # expected - ValueError
    with pytest.raises(ValueError):
        await AsyncProfile(
            profile_name="PYTHON_INVALID_PROFILE",
            attributes=ProfileAttributes(
                credential_name="OCI_CRED", provider=invalid_provider
            ),
        )


async def test_1312():
    # provider=None
    # expected - ORA-20047: Either provider or provider_endpoint must be specified
    with pytest.raises(oracledb.DatabaseError):
        await AsyncProfile(
            profile_name="PYTHON_INVALID_PROFILE",
            attributes=ProfileAttributes(
                credential_name="OCI_CRED", provider=None
            ),
        )


@pytest.mark.parametrize(
    "invalid_profile_name",
    [
        "",
        None,
    ],
)
async def test_1313(invalid_profile_name, min_profile_attributes):
    """Create Profile with empty profile_name"""
    # expected - ValueError
    with pytest.raises(ValueError):
        await AsyncProfile(
            profile_name=invalid_profile_name,
            attributes=min_profile_attributes,
        )


async def test_1314():
    """List Profile with invalid regex"""
    # expected - ORA-12726: unmatched bracket in regular expression
    with pytest.raises(oracledb.DatabaseError):
        profiles = [
            profile
            async for profile in AsyncProfile.list(
                profile_name_pattern="[*invalid"
            )
        ]
