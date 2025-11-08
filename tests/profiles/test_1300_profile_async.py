# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1300 - Module for testing the AsyncProfile proxy object
"""
import uuid

import oracledb
import pytest
import select_ai
from select_ai import AsyncProfile, ProfileAttributes

PYSAI_ASYNC_1300_PROFILE = f"PYSAI_ASYNC_1300_{uuid.uuid4().hex.upper()}"
PYSAI_ASYNC_1300_PROFILE_2 = f"PYSAI_ASYNC_1300_2_{uuid.uuid4().hex.upper()}"
PYSAI_ASYNC_1300_MIN_ATTR_PROFILE = (
    f"PYSAI_ASYNC_1300_MIN_{uuid.uuid4().hex.upper()}"
)
PYSAI_ASYNC_1300_DUP_PROFILE = (
    f"PYSAI_ASYNC_1300_DUP_{uuid.uuid4().hex.upper()}"
)


@pytest.fixture(scope="module")
async def python_gen_ai_profile(profile_attributes):
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_profile_2(profile_attributes):
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE_2,
        description="OCI GENAI Profile 2",
        attributes=profile_attributes,
    )
    await profile.create(replace=True)
    yield profile
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_min_attr_profile(min_profile_attributes):
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_MIN_ATTR_PROFILE,
        attributes=min_profile_attributes,
        description=None,
    )
    yield profile
    await profile.delete(force=True)


@pytest.fixture
async def python_gen_ai_duplicate_profile(min_profile_attributes):
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_DUP_PROFILE,
        attributes=min_profile_attributes,
    )
    yield profile
    await profile.delete(force=True)


def test_1300(python_gen_ai_profile, profile_attributes):
    """Create basic Profile"""
    assert python_gen_ai_profile.profile_name == PYSAI_ASYNC_1300_PROFILE
    assert python_gen_ai_profile.attributes == profile_attributes
    assert python_gen_ai_profile.description == "OCI GENAI Profile"


def test_1301(python_gen_ai_profile_2, profile_attributes):
    """Create Profile using create method"""
    assert python_gen_ai_profile_2.profile_name == PYSAI_ASYNC_1300_PROFILE_2
    assert python_gen_ai_profile_2.attributes == profile_attributes
    assert python_gen_ai_profile_2.description == "OCI GENAI Profile 2"


async def test_1302(profile_attributes):
    """Create duplicate profile with replace=True"""
    duplicate = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE,
        attributes=profile_attributes,
        replace=True,
    )
    assert duplicate.profile_name == PYSAI_ASYNC_1300_PROFILE
    assert duplicate.attributes == profile_attributes
    assert duplicate.description is None


def test_1303(python_gen_ai_min_attr_profile, min_profile_attributes):
    """Create Profile with minimum required attributes"""
    assert (
        python_gen_ai_min_attr_profile.profile_name
        == PYSAI_ASYNC_1300_MIN_ATTR_PROFILE
    )
    assert python_gen_ai_min_attr_profile.attributes == min_profile_attributes
    assert python_gen_ai_min_attr_profile.description is None


async def test_1304():
    """List profiles without regex"""
    profile_list = [profile async for profile in AsyncProfile.list()]
    profile_names = set(profile.profile_name for profile in profile_list)
    descriptions = set(profile.description for profile in profile_list)
    assert PYSAI_ASYNC_1300_PROFILE in profile_names
    assert PYSAI_ASYNC_1300_PROFILE_2 in profile_names
    assert PYSAI_ASYNC_1300_MIN_ATTR_PROFILE in profile_names
    assert "OCI GENAI Profile 2" in descriptions


async def test_1305():
    """List profiles with regex"""
    profile_list = [
        profile
        async for profile in AsyncProfile.list(
            profile_name_pattern="^PYSAI_ASYNC_1300"
        )
    ]
    profile_names = set(profile.profile_name for profile in profile_list)
    descriptions = set(profile.description for profile in profile_list)
    assert PYSAI_ASYNC_1300_PROFILE in profile_names
    assert PYSAI_ASYNC_1300_PROFILE_2 in profile_names
    assert PYSAI_ASYNC_1300_MIN_ATTR_PROFILE in profile_names
    assert "OCI GENAI Profile 2" in descriptions


async def test_1306(profile_attributes):
    """Get attributes for a Profile"""
    profile = await AsyncProfile(PYSAI_ASYNC_1300_PROFILE)
    fetched_attributes = await profile.get_attributes()
    assert fetched_attributes == profile_attributes


async def test_1307():
    """Set attributes for a Profile"""
    profile = await AsyncProfile(PYSAI_ASYNC_1300_PROFILE)
    assert profile.attributes.provider.model is None
    await profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    assert profile.attributes.provider.model == "meta.llama-3.1-70b-instruct"


async def test_1308(oci_credential):
    """Set multiple attributes for a Profile"""
    profile = await AsyncProfile(PYSAI_ASYNC_1300_PROFILE)
    profile_attrs = ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=select_ai.OCIGenAIProvider(
            model="meta.llama-4-maverick-17b-128e-instruct-fp8",
            region="us-chicago-1",
            oci_apiformat="GENERIC",
        ),
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
            await profile
            async for profile in AsyncProfile.list(
                profile_name_pattern="[*invalid"
            )
        ]


async def test_1315(profile_attributes):
    """Test AsyncProfile.fetch"""
    async_profile = await AsyncProfile.fetch(
        profile_name=PYSAI_ASYNC_1300_PROFILE_2
    )
    assert async_profile.profile_name == PYSAI_ASYNC_1300_PROFILE_2
    assert async_profile.attributes == profile_attributes
    assert async_profile.description == "OCI GENAI Profile 2"
