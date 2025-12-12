# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1200 - Module for testing the Profile proxy object
"""
import collections
import uuid

import oracledb
import pytest
import select_ai
from select_ai import Profile, ProfileAttributes

PYSAI_1200_PROFILE = f"PYSAI_1200_{uuid.uuid4().hex.upper()}"
PYSAI_1200_PROFILE_2 = f"PYSAI_1200_2_{uuid.uuid4().hex.upper()}"
PYSAI_1200_MIN_ATTR_PROFILE = f"PYSAI_1200_MIN_{uuid.uuid4().hex.upper()}"
PYSAI_1200_DUP_PROFILE = f"PYSAI_1200_DUP_{uuid.uuid4().hex.upper()}"


@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_1200_PROFILE,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def python_gen_ai_profile_2(profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_1200_PROFILE_2,
        description="OCI GENAI Profile 2",
        attributes=profile_attributes,
    )
    profile.create(replace=True)
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def python_gen_ai_min_attr_profile(min_profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_1200_MIN_ATTR_PROFILE,
        attributes=min_profile_attributes,
        description=None,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture
def python_gen_ai_duplicate_profile(min_profile_attributes):
    profile = Profile(
        profile_name=PYSAI_1200_DUP_PROFILE,
        attributes=min_profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def python_gen_ai_neg_feedback(cursor, python_gen_ai_profile):
    feedback_metadata = collections.namedtuple(
        "FeedbackMetadata",
        [
            "prompt",
            "action",
            "feedback_response",
            "feedback_content",
            "sql_text",
        ],
    )
    cursor.execute(
        f"""BEGIN
             dbms_cloud_ai.set_profile('{python_gen_ai_profile.profile_name}');
            END;"""
    )
    prompt = "Total points of each gymnasts"
    action = select_ai.Action.SHOWSQL
    sql_text = f"select ai {action.value} {prompt}"
    cursor.execute(sql_text)
    feedback_response = "SELECT * from gymnast"
    feedback_content = "print in ascending order of total_points"
    python_gen_ai_profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=feedback_response,
        feedback_content=feedback_content,
    )
    yield feedback_metadata(
        prompt=prompt,
        action=action,
        feedback_response=feedback_response,
        feedback_content=feedback_content,
        sql_text=sql_text,
    )
    python_gen_ai_profile.delete_feedback(prompt_spec=(prompt, action))


@pytest.fixture(scope="module")
def python_gen_ai_pos_feedback(cursor, python_gen_ai_profile):
    feedback_metadata = collections.namedtuple(
        "PositiveFeedbackMetadata",
        ["prompt", "action", "sql_text"],
    )
    cursor.execute(
        f"""BEGIN
             dbms_cloud_ai.set_profile('{python_gen_ai_profile.profile_name}');
            END;
       """
    )
    prompt = "Lists the name of all people"
    action = select_ai.Action.SHOWSQL
    sql_text = f"select ai {action.value} {prompt}"
    cursor.execute(sql_text)
    python_gen_ai_profile.add_positive_feedback(
        prompt_spec=(prompt, action),
    )
    yield feedback_metadata(
        prompt=prompt,
        action=action,
        sql_text=sql_text,
    )
    python_gen_ai_profile.delete_feedback(prompt_spec=(prompt, action))


def test_1200(python_gen_ai_profile, profile_attributes):
    """Create basic Profile"""
    assert python_gen_ai_profile.profile_name == PYSAI_1200_PROFILE
    assert python_gen_ai_profile.attributes == profile_attributes
    assert python_gen_ai_profile.description == "OCI GENAI Profile"


def test_1201(python_gen_ai_profile_2, profile_attributes):
    """Create Profile using create method"""
    assert python_gen_ai_profile_2.profile_name == PYSAI_1200_PROFILE_2
    assert python_gen_ai_profile_2.attributes == profile_attributes
    assert python_gen_ai_profile_2.description == "OCI GENAI Profile 2"


def test_1202(profile_attributes):
    """Create duplicate profile with replace=True"""
    duplicate = Profile(
        profile_name=PYSAI_1200_PROFILE,
        attributes=profile_attributes,
        replace=True,
    )
    assert duplicate.profile_name == PYSAI_1200_PROFILE
    assert duplicate.attributes == profile_attributes
    assert duplicate.description is None


def test_1203(python_gen_ai_min_attr_profile, min_profile_attributes):
    """Create Profile with minimum required attributes"""
    assert (
        python_gen_ai_min_attr_profile.profile_name
        == PYSAI_1200_MIN_ATTR_PROFILE
    )
    assert python_gen_ai_min_attr_profile.attributes == min_profile_attributes
    assert python_gen_ai_min_attr_profile.description is None


def test_1204():
    """List profiles without regex"""
    profile_list = list(Profile.list())
    profile_names = set(profile.profile_name for profile in profile_list)
    descriptions = set(profile.description for profile in profile_list)
    assert PYSAI_1200_PROFILE in profile_names
    assert PYSAI_1200_PROFILE_2 in profile_names
    assert PYSAI_1200_MIN_ATTR_PROFILE in profile_names
    assert "OCI GENAI Profile 2" in descriptions


def test_1205():
    """List profiles with regex"""
    profile_list = list(Profile.list(profile_name_pattern="^PYSAI_1200"))
    profile_names = set(profile.profile_name for profile in profile_list)
    descriptions = set(profile.description for profile in profile_list)
    assert PYSAI_1200_PROFILE in profile_names
    assert PYSAI_1200_PROFILE_2 in profile_names
    assert PYSAI_1200_MIN_ATTR_PROFILE in profile_names
    assert "OCI GENAI Profile 2" in descriptions


def test_1206(profile_attributes):
    """Get attributes for a Profile"""
    profile = Profile(PYSAI_1200_PROFILE)
    fetched_attributes = profile.get_attributes()
    assert fetched_attributes == profile_attributes


def test_1207():
    """Set attributes for a Profile"""
    profile = Profile(PYSAI_1200_PROFILE)
    assert profile.attributes.provider.model is None
    profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    assert profile.attributes.provider.model == "meta.llama-3.1-70b-instruct"


def test_1208(oci_credential):
    """Set multiple attributes for a Profile"""
    profile = Profile(PYSAI_1200_PROFILE)
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
    profile.set_attributes(profile_attrs)
    assert profile.attributes.object_list == [
        {"owner": "ADMIN", "name": "gymnasts"}
    ]
    assert profile.attributes.comments is True
    fetched_attributes = profile.get_attributes()
    print(fetched_attributes.provider)
    assert fetched_attributes == profile_attrs


def test_1209(python_gen_ai_duplicate_profile):
    """Create duplicate profile without replace"""
    # expected - ProfileExistsError
    with pytest.raises(select_ai.errors.ProfileExistsError):
        Profile(
            profile_name=python_gen_ai_duplicate_profile.profile_name,
            attributes=python_gen_ai_duplicate_profile.attributes,
        )


def test_1210(python_gen_ai_duplicate_profile):
    """Create duplicate profile with replace=False"""
    # expected - select_ai.ProfileExistsError
    with pytest.raises(select_ai.errors.ProfileExistsError):
        Profile(
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
def test_1211(invalid_provider):
    """Create Profile with invalid providers"""
    # expected - ValueError
    with pytest.raises(ValueError):
        Profile(
            profile_name="PYTHON_INVALID_PROFILE",
            attributes=ProfileAttributes(
                credential_name="OCI_CRED", provider=invalid_provider
            ),
        )


def test_1212():
    # provider=None
    # expected - ORA-20047: Either provider or provider_endpoint must be specified
    with pytest.raises(oracledb.DatabaseError):
        Profile(
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
def test_1213(invalid_profile_name, min_profile_attributes):
    """Create Profile with empty profile_name"""
    # expected - ValueError
    with pytest.raises(ValueError):
        Profile(
            profile_name=invalid_profile_name,
            attributes=min_profile_attributes,
        )


def test_1214():
    """List Profile with invalid regex"""
    # expected - ORA-12726: unmatched bracket in regular expression
    with pytest.raises(oracledb.DatabaseError):
        list(Profile().list(profile_name_pattern="[*invalid"))


def test_1215(profile_attributes):
    """Test Profile.fetch"""
    profile = Profile.fetch(profile_name=PYSAI_1200_PROFILE_2)
    assert profile.profile_name == PYSAI_1200_PROFILE_2
    assert profile.attributes == profile_attributes
    assert profile.description == "OCI GENAI Profile 2"


def test_1216(cursor, python_gen_ai_profile, python_gen_ai_neg_feedback):
    """Test profile negative feedback"""
    cursor.execute(
        f"select CONTENT, ATTRIBUTES "
        f"from {python_gen_ai_profile.profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB "
        f"where JSON_VALUE(attributes, '$.sql_text') = '{python_gen_ai_neg_feedback.sql_text}'"
    )
    data = cursor.fetchone()
    assert data[0].read() == python_gen_ai_neg_feedback.prompt
    feedback_attributes = data[1]
    assert (
        feedback_attributes["sql_text"] == python_gen_ai_neg_feedback.sql_text
    )
    assert (
        feedback_attributes["feedback_content"]
        == python_gen_ai_neg_feedback.feedback_content
    )


def test_1217(cursor, python_gen_ai_profile, python_gen_ai_pos_feedback):
    """Test profile positive feedback"""
    cursor.execute(
        f"select CONTENT, ATTRIBUTES "
        f"from {python_gen_ai_profile.profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB "
        f"where JSON_VALUE(attributes, '$.sql_text') = '{python_gen_ai_pos_feedback.sql_text}'"
    )
    data = cursor.fetchone()
    assert data[0].read() == python_gen_ai_pos_feedback.prompt
    feedback_attributes = data[1]
    assert (
        feedback_attributes["sql_text"] == python_gen_ai_pos_feedback.sql_text
    )


def test_1218(python_gen_ai_profile):
    """Test translate"""
    response = python_gen_ai_profile.translate(
        text="Thank you", source_language="en", target_language="de"
    )
    assert response == "Danke"
