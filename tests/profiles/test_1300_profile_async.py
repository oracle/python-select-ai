# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
1300 - Module for testing the AsyncProfile proxy object
"""
import collections
import logging
import uuid

import oracledb
import pytest
import select_ai
from select_ai import AsyncProfile, ProfileAttributes

logger = logging.getLogger(__name__)
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
    logger.info("Creating async profile %s", PYSAI_ASYNC_1300_PROFILE)
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    logger.debug("AsyncProfile = \n %s", profile)
    yield profile
    logger.info("Deleting async profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_profile_2(profile_attributes):
    logger.info("Creating async profile %s", PYSAI_ASYNC_1300_PROFILE_2)
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE_2,
        description="OCI GENAI Profile 2",
        attributes=profile_attributes,
    )
    await profile.create(replace=True)
    logger.debug("AsyncProfile = \n %s", profile)
    yield profile
    logger.info("Deleting async profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_min_attr_profile(min_profile_attributes):
    logger.info(
        "Creating async profile with minimum attributes %s",
        PYSAI_ASYNC_1300_MIN_ATTR_PROFILE,
    )
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_MIN_ATTR_PROFILE,
        attributes=min_profile_attributes,
        description=None,
    )
    logger.debug("AsyncProfile = \n %s", profile)
    yield profile
    logger.info("Deleting async profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture
async def python_gen_ai_duplicate_profile(min_profile_attributes):
    logger.info(
        "Creating duplicate async profile %s", PYSAI_ASYNC_1300_DUP_PROFILE
    )
    profile = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_DUP_PROFILE,
        attributes=min_profile_attributes,
    )
    logger.debug("AsyncProfile = \n %s", profile)
    yield profile
    logger.info("Cleaning up duplicate async profile %s", profile.profile_name)
    await profile.delete(force=True)


@pytest.fixture(scope="module")
async def python_gen_ai_neg_feedback(async_cursor, python_gen_ai_profile):
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
    await async_cursor.execute(
        f"""BEGIN
             dbms_cloud_ai.set_profile('{python_gen_ai_profile.profile_name}');
            END;
       """
    )
    prompt = "Total points of each gymnasts"
    action = select_ai.Action.SHOWSQL
    sql_text = f"select ai {action.value} {prompt}"
    await async_cursor.execute(sql_text)
    feedback_response = "SELECT * from gymnast"
    feedback_content = "print in ascending order of total_points"
    logger.info(
        "Adding negative feedback for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await python_gen_ai_profile.add_negative_feedback(
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
    logger.info(
        "Removing negative feedback for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await python_gen_ai_profile.delete_feedback(prompt_spec=(prompt, action))


@pytest.fixture(scope="module")
async def python_gen_ai_pos_feedback(async_cursor, python_gen_ai_profile):
    feedback_metadata = collections.namedtuple(
        "PositiveFeedbackMetadata",
        ["prompt", "action", "sql_text"],
    )
    await async_cursor.execute(
        f"""BEGIN
             dbms_cloud_ai.set_profile('{python_gen_ai_profile.profile_name}');
            END;
       """
    )
    prompt = "Lists the name of all people"
    action = select_ai.Action.SHOWSQL
    sql_text = f"select ai {action.value} {prompt}"
    await async_cursor.execute(sql_text)
    logger.info(
        "Adding positive feedback for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await python_gen_ai_profile.add_positive_feedback(
        prompt_spec=(prompt, action),
    )
    yield feedback_metadata(
        prompt=prompt,
        action=action,
        sql_text=sql_text,
    )
    logger.info(
        "Removing positive feedback for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await python_gen_ai_profile.delete_feedback(prompt_spec=(prompt, action))


def test_1300(python_gen_ai_profile, profile_attributes):
    """Create basic Profile"""
    logger.info(
        "Validating async profile %s", python_gen_ai_profile.profile_name
    )
    assert python_gen_ai_profile.profile_name == PYSAI_ASYNC_1300_PROFILE
    assert python_gen_ai_profile.attributes == profile_attributes
    assert python_gen_ai_profile.description == "OCI GENAI Profile"


def test_1301(python_gen_ai_profile_2, profile_attributes):
    """Create Profile using create method"""
    logger.info(
        "Validating async profile created via create %s",
        python_gen_ai_profile_2.profile_name,
    )
    assert python_gen_ai_profile_2.profile_name == PYSAI_ASYNC_1300_PROFILE_2
    assert python_gen_ai_profile_2.attributes == profile_attributes
    assert python_gen_ai_profile_2.description == "OCI GENAI Profile 2"


async def test_1302(profile_attributes):
    """Create duplicate profile with replace=True"""
    logger.info("Creating duplicate async profile with replace=True")
    duplicate = await AsyncProfile(
        profile_name=PYSAI_ASYNC_1300_PROFILE,
        attributes=profile_attributes,
        replace=True,
    )
    logger.info(
        "Validating duplicate async profile %s", duplicate.profile_name
    )
    assert duplicate.profile_name == PYSAI_ASYNC_1300_PROFILE
    assert duplicate.attributes == profile_attributes
    assert duplicate.description is None


def test_1303(python_gen_ai_min_attr_profile, min_profile_attributes):
    """Create Profile with minimum required attributes"""
    logger.info(
        "Validating async minimum attribute profile %s",
        python_gen_ai_min_attr_profile.profile_name,
    )
    assert (
        python_gen_ai_min_attr_profile.profile_name
        == PYSAI_ASYNC_1300_MIN_ATTR_PROFILE
    )
    assert python_gen_ai_min_attr_profile.attributes == min_profile_attributes
    assert python_gen_ai_min_attr_profile.description is None


async def test_1304():
    """List profiles without regex"""
    logger.info("Listing async profiles without regex")
    profile_list = [profile async for profile in AsyncProfile.list()]
    profile_names = set(profile.profile_name for profile in profile_list)
    descriptions = set(profile.description for profile in profile_list)
    assert PYSAI_ASYNC_1300_PROFILE in profile_names
    assert PYSAI_ASYNC_1300_PROFILE_2 in profile_names
    assert PYSAI_ASYNC_1300_MIN_ATTR_PROFILE in profile_names
    assert "OCI GENAI Profile 2" in descriptions


async def test_1305():
    """List profiles with regex"""
    logger.info("Listing async profiles with regex pattern")
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
    logger.info(
        "Fetching attributes for async profile %s", PYSAI_ASYNC_1300_PROFILE
    )
    profile = await AsyncProfile(PYSAI_ASYNC_1300_PROFILE)
    fetched_attributes = await profile.get_attributes()
    assert fetched_attributes == profile_attributes


async def test_1307():
    """Set attributes for a Profile"""
    logger.info(
        "Setting single attribute on async profile %s",
        PYSAI_ASYNC_1300_PROFILE,
    )
    profile = await AsyncProfile(PYSAI_ASYNC_1300_PROFILE)
    assert profile.attributes.provider.model is None
    await profile.set_attribute(
        attribute_name="model", attribute_value="meta.llama-3.1-70b-instruct"
    )
    assert profile.attributes.provider.model == "meta.llama-3.1-70b-instruct"


async def test_1308(oci_credential):
    """Set multiple attributes for a Profile"""
    logger.info(
        "Setting multiple attributes for async profile %s",
        PYSAI_ASYNC_1300_PROFILE,
    )
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
    logger.debug(
        "Fetched async provider attributes: %s", fetched_attributes.provider
    )
    assert fetched_attributes == profile_attrs


async def test_1309(python_gen_ai_duplicate_profile):
    """Create duplicate profile without replace"""
    # expected - ProfileExistsError
    logger.info(
        "Expecting ProfileExistsError for duplicate async profile %s",
        python_gen_ai_duplicate_profile.profile_name,
    )
    with pytest.raises(select_ai.errors.ProfileExistsError):
        await AsyncProfile(
            profile_name=python_gen_ai_duplicate_profile.profile_name,
            attributes=python_gen_ai_duplicate_profile.attributes,
        )


async def test_1310(python_gen_ai_duplicate_profile):
    """Create duplicate profile with replace=False"""
    # expected - select_ai.ProfileExistsError
    logger.info(
        "Expecting ProfileExistsError with replace=False for async profile %s",
        python_gen_ai_duplicate_profile.profile_name,
    )
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
    logger.info(
        "Validating async invalid provider handling: %s", invalid_provider
    )
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
    logger.info("Validating async provider=None raises DatabaseError")
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
    logger.info(
        "Validating async empty profile name handling: %s",
        invalid_profile_name,
    )
    with pytest.raises(ValueError):
        await AsyncProfile(
            profile_name=invalid_profile_name,
            attributes=min_profile_attributes,
        )


async def test_1314():
    """List Profile with invalid regex"""
    # expected - ORA-12726: unmatched bracket in regular expression
    logger.info("Validating async invalid regex handling during list")
    with pytest.raises(oracledb.DatabaseError):
        profiles = [
            await profile
            async for profile in AsyncProfile.list(
                profile_name_pattern="[*invalid"
            )
        ]


async def test_1315(profile_attributes):
    """Test AsyncProfile.fetch"""
    logger.info("Fetching async profile %s", PYSAI_ASYNC_1300_PROFILE_2)
    async_profile = await AsyncProfile.fetch(
        profile_name=PYSAI_ASYNC_1300_PROFILE_2
    )
    assert async_profile.profile_name == PYSAI_ASYNC_1300_PROFILE_2
    assert async_profile.attributes == profile_attributes
    assert async_profile.description == "OCI GENAI Profile 2"


async def test_1316(
    async_cursor, python_gen_ai_profile, python_gen_ai_neg_feedback
):
    """Test profile negative feedback"""
    logger.info(
        "Validating negative feedback persistence for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await async_cursor.execute(
        f"select CONTENT, ATTRIBUTES "
        f"from {python_gen_ai_profile.profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB "
        f"where JSON_VALUE(attributes, '$.sql_text') = '{python_gen_ai_neg_feedback.sql_text}'"
    )
    data = await async_cursor.fetchone()
    prompt = await data[0].read()
    assert prompt == python_gen_ai_neg_feedback.prompt
    feedback_attributes = data[1]
    assert (
        feedback_attributes["sql_text"] == python_gen_ai_neg_feedback.sql_text
    )
    assert (
        feedback_attributes["feedback_content"]
        == python_gen_ai_neg_feedback.feedback_content
    )


async def test_1317(
    async_cursor, python_gen_ai_profile, python_gen_ai_pos_feedback
):
    """Test profile positive feedback"""
    logger.info(
        "Validating positive feedback persistence for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    await async_cursor.execute(
        f"select CONTENT, ATTRIBUTES "
        f"from {python_gen_ai_profile.profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB "
        f"where JSON_VALUE(attributes, '$.sql_text') = '{python_gen_ai_pos_feedback.sql_text}'"
    )
    data = await async_cursor.fetchone()
    prompt = await data[0].read()
    assert prompt == python_gen_ai_pos_feedback.prompt
    feedback_attributes = data[1]
    assert (
        feedback_attributes["sql_text"] == python_gen_ai_pos_feedback.sql_text
    )


async def test_1318(python_gen_ai_profile):
    """Test translate"""
    logger.info(
        "Testing translate for async profile %s",
        python_gen_ai_profile.profile_name,
    )
    response = await python_gen_ai_profile.translate(
        text="Thank you", source_language="en", target_language="de"
    )
    assert response == "Danke"
