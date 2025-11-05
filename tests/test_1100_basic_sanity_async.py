# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1100 - Module for testing basic sanity using AsyncProfile
"""
import uuid

import pytest
import select_ai
from pandas import DataFrame

ASYNC_PROFILE_NAME = f"PYSAI_ASYNC_1200_{uuid.uuid4().hex.upper()}"
PROFILE_DESCRIPTION = "OCI Gen AI Basic Test Profile"


@pytest.fixture(scope="module")
async def async_oci_gen_ai_profile(
    async_connect, oci_credential, oci_compartment_id, test_env
):
    profile = await select_ai.AsyncProfile(
        profile_name=ASYNC_PROFILE_NAME,
        description=PROFILE_DESCRIPTION,
        attributes=select_ai.ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=[{"owner": test_env.test_user, "name": "gymnast"}],
            provider=select_ai.OCIGenAIProvider(
                oci_compartment_id=oci_compartment_id, oci_apiformat="GENERIC"
            ),
        ),
    )
    yield profile
    await profile.delete(force=True)


async def test_1100(async_oci_gen_ai_profile):
    assert async_oci_gen_ai_profile.profile_name == ASYNC_PROFILE_NAME
    assert (
        async_oci_gen_ai_profile.attributes
        == await async_oci_gen_ai_profile.get_attributes()
    )


async def test_1101():
    "test list profile by name"
    profiles = [
        profile
        async for profile in select_ai.AsyncProfile.list(
            profile_name_pattern=ASYNC_PROFILE_NAME
        )
    ]
    profile_names = set([profile.profile_name for profile in profiles])
    assert ASYNC_PROFILE_NAME in profile_names


async def test_1102():
    "test list all profiles"
    profiles = [profile async for profile in select_ai.AsyncProfile.list()]
    profile_names = set([profile.profile_name for profile in profiles])
    assert ASYNC_PROFILE_NAME in profile_names


async def test_1103(async_oci_gen_ai_profile):
    """Narrate for simple NL prompt"""
    prompt = "What is a database?"
    narrate = await async_oci_gen_ai_profile.narrate(prompt)
    assert narrate is not None
    assert isinstance(narrate, str)


async def test_1104(async_oci_gen_ai_profile):
    """Chat for a simple NL prompt"""
    await async_oci_gen_ai_profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-405b-instruct"
    )
    prompt = "What is a database?"
    chat = await async_oci_gen_ai_profile.chat(prompt)
    assert chat is not None
    assert isinstance(chat, str)


async def test_1105(async_oci_gen_ai_profile):
    """Run SQL for a simple NL prompt"""
    await async_oci_gen_ai_profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-405b-instruct"
    )
    prompt = "How many gymnast in the table?"
    df = await async_oci_gen_ai_profile.run_sql(prompt)
    assert df is not None
    assert isinstance(df, DataFrame)


async def test_1106(test_env):
    "test profile merge"
    profile = await select_ai.AsyncProfile(
        profile_name=ASYNC_PROFILE_NAME,
        attributes=select_ai.ProfileAttributes(
            object_list=[{"owner": test_env.test_user}],
        ),
        merge=True,
    )
    assert profile.profile_name == ASYNC_PROFILE_NAME
    assert profile.description == PROFILE_DESCRIPTION
    assert profile.attributes.object_list == [{"owner": test_env.test_user}]
    attributes = await profile.get_attributes()
    assert profile.attributes.provider == attributes.provider
    assert profile.attributes.credential_name == attributes.credential_name
