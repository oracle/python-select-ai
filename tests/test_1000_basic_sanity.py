# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1000 - Module for testing basic sanity
"""
import uuid

import pytest
import select_ai
from pandas import DataFrame

PROFILE_NAME = f"PYSAI_1000_{uuid.uuid4().hex.upper()}"
PROFILE_DESCRIPTION = "OCI Gen AI Basic Test Profile"


@pytest.fixture(scope="module")
def oci_gen_ai_profile(oci_credential, oci_compartment_id, test_env):
    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
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
    profile.delete(force=True)


def test_1000(oci_gen_ai_profile):
    "test profile attributes"
    assert oci_gen_ai_profile.profile_name == PROFILE_NAME
    assert oci_gen_ai_profile.description == PROFILE_DESCRIPTION
    assert oci_gen_ai_profile.attributes == oci_gen_ai_profile.get_attributes()
    assert (
        oci_gen_ai_profile.attributes.provider
        == oci_gen_ai_profile.get_attributes().provider
    )


def test_1001():
    "test list profile by name"
    profiles = set(
        profile.profile_name
        for profile in select_ai.Profile.list(
            profile_name_pattern=PROFILE_NAME
        )
    )
    assert PROFILE_NAME in profiles


def test_1002():
    "test list all profiles"
    profiles = set(
        profile.profile_name for profile in select_ai.Profile.list()
    )
    assert PROFILE_NAME in profiles


def test_1003(oci_gen_ai_profile):
    """Narrate for simple NL prompt"""
    prompt = "What is a database?"
    narrate = oci_gen_ai_profile.narrate(prompt)
    assert narrate is not None
    assert isinstance(narrate, str)


def test_1004(oci_gen_ai_profile):
    """Chat for a simple NL prompt"""
    oci_gen_ai_profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-405b-instruct"
    )
    prompt = "What is a database?"
    chat = oci_gen_ai_profile.chat(prompt)
    assert chat is not None
    assert isinstance(chat, str)


def test_1005(oci_gen_ai_profile):
    """Run SQL for a simple NL prompt"""
    oci_gen_ai_profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-405b-instruct"
    )
    prompt = "How many gymnast in the table?"
    df = oci_gen_ai_profile.run_sql(prompt)
    assert df is not None
    assert isinstance(df, DataFrame)


def test_1006(test_env):
    "test profile merge"
    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        attributes=select_ai.ProfileAttributes(
            object_list=[{"owner": test_env.test_user}],
        ),
        merge=True,
    )
    assert profile.profile_name == PROFILE_NAME
    assert profile.description == PROFILE_DESCRIPTION
    assert profile.attributes.object_list == [{"owner": test_env.test_user}]
    assert profile.attributes.provider == profile.get_attributes().provider
    assert (
        profile.attributes.credential_name
        == profile.get_attributes().credential_name
    )
