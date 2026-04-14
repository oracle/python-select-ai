# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
4100 - Async profile feedback API tests
"""
import logging
import uuid
import oracledb
import pytest
import select_ai
from select_ai.action import Action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_ACTIVE_ASYNC_CURSOR = None

PROFILE_PREFIX = "PYSAI_TEST_FEEDBACK_ASYNC_4100"
PROFILE_NAME = f"{PROFILE_PREFIX}_{uuid.uuid4().hex.upper()}"
PROFILE_DESCRIPTION = "OCI Gen AI Test Profile"
PROMPT = "Total points of each gymnasts"
SHOWSQL_SQL_ID = "ahgttusrvh9x5"
RUNSQL_SQL_ID = "6s20ukn8j3p5j"
EXPLAINSQL_SQL_ID = "2a617cynwfm36"
PROFILE_OBJECT_NAMES = ("gymnast", "people")
WARMUP_STATEMENTS = (
    f"select ai showsql {PROMPT}",
    f"select ai runsql {PROMPT}",
    f"select ai explainsql {PROMPT}",
)


def _assert_db_error(exc_info, expected_code):
    assert isinstance(exc_info.value, oracledb.DatabaseError)
    (error,) = exc_info.value.args
    assert error.code == expected_code
    return error


async def _set_profile_and_warm_up(profile_name, async_cursor):
    await async_cursor.execute(
        """
        BEGIN
           dbms_cloud_ai.set_profile(:profile_name);
        END;
        """,
        profile_name=profile_name,
    )
    for statement in WARMUP_STATEMENTS:
        await async_cursor.execute(statement)


async def _log_feedback_vecindex_rows(profile):
    if _ACTIVE_ASYNC_CURSOR is None:
        raise RuntimeError("async_cursor fixture is not available")
    table_name = f"{profile.profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB"
    await _ACTIVE_ASYNC_CURSOR.execute(
        f"select CONTENT, ATTRIBUTES from {table_name}"
    )
    rows = await _ACTIVE_ASYNC_CURSOR.fetchall()
    logger.info("Feedback vecindex rows: %s", rows)


@pytest.fixture(scope="module")
async def profile(oci_credential, oci_compartment_id, test_env, async_cursor):
    object_list = [
        {"owner": test_env.test_user, "name": object_name}
        for object_name in PROFILE_OBJECT_NAMES
    ]
    profile = await select_ai.AsyncProfile(
        profile_name=PROFILE_NAME,
        description=PROFILE_DESCRIPTION,
        replace=True,
        attributes=select_ai.ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=object_list,
            provider=select_ai.OCIGenAIProvider(
                oci_compartment_id=oci_compartment_id,
                oci_apiformat="GENERIC",
            ),
        ),
    )
    await _set_profile_and_warm_up(profile.profile_name, async_cursor)

    yield profile
    await profile.delete(force=True)


@pytest.fixture(autouse=True)
async def active_async_cursor(async_cursor):
    global _ACTIVE_ASYNC_CURSOR
    _ACTIVE_ASYNC_CURSOR = async_cursor
    yield
    _ACTIVE_ASYNC_CURSOR = None

############################################### NEGATIVE FEEDBACK TESTS
async def test_4101(profile, async_cursor):
    """Add negative feedback using SHOWSQL prompt_spec, response, and feedback_content."""
    prompt = PROMPT
    action = Action.SHOWSQL
    response = (
        "SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 "
        "ON p5.id = g5.id ORDER BY p4.name ASC"
    )
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4102(profile, async_cursor):
    """Add negative feedback using RUNSQL prompt_spec, response, and feedback_content."""
    prompt = PROMPT
    action = Action.RUNSQL
    response = (
        "SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 "
        "ON p5.id = g5.id ORDER BY p4.name ASC"
    )
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4103(profile, async_cursor):
    """Add negative feedback using EXPLAINSQL prompt_spec, response, and feedback_content."""
    prompt = PROMPT
    action = Action.EXPLAINSQL
    response = (
        "SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 "
        "ON p5.id = g5.id ORDER BY p4.name ASC"
    )
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4104(profile, async_cursor):
    """Add negative feedback using SHOWSQL sql_id, response, and feedback_content."""
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p4.name, g4.total_points FROM people p4 JOIN gymnast g4 "
        "ON p4.id = g4.id ORDER BY p4.name DESC"
    )
    feedback_content = "print in descending order of name"
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=%s",
        sql_id,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4105(profile, async_cursor):
    """Add negative feedback using RUNSQL sql_id, response, and feedback_content."""
    sql_id = RUNSQL_SQL_ID
    response = (
        "SELECT p4.name, g4.total_points FROM people p4 JOIN gymnast g4 "
        "ON p4.id = g4.id ORDER BY p4.name DESC"
    )
    feedback_content = "print in descending order of name"
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=%s",
        sql_id,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4106(profile, async_cursor):
    """Add negative feedback using EXPLAINSQL sql_id, response, and feedback_content."""
    sql_id = EXPLAINSQL_SQL_ID
    response = (
        "SELECT p4.name, g4.total_points FROM people p4 JOIN gymnast g4 "
        "ON p4.id = g4.id ORDER BY p4.name DESC"
    )
    feedback_content = "print in descending order of name"
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=%s",
        sql_id,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4107(profile, async_cursor):
    """Attempt negative feedback with both prompt_spec and sql_id."""
    prompt = PROMPT
    action = Action.SHOWSQL
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 "
        "ON p1.id = g1.id ORDER BY g1.total_points DESC"
    )
    feedback_content = "print in descending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=%s response=%s feedback_content=%s",
        prompt,
        action,
        sql_id,
        response,
        feedback_content,
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        await profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])


async def test_4108(profile, async_cursor):
    """Attempt negative feedback without a response."""
    prompt = PROMPT
    action = Action.SHOWSQL
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=None feedback_content=%s",
        prompt,
        action,
        feedback_content,
    )
    with pytest.raises(AttributeError) as exc_info:
        await profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            feedback_content=feedback_content,
        )
    assert isinstance(exc_info.value, AttributeError)
    logger.error("%s", str(exc_info.value).splitlines()[0])


async def test_4109(profile, async_cursor):
    """Add negative feedback with sql_id and response but without feedback_content."""
    action = Action.SHOWSQL
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 "
        "ON p6.id = g6.id ORDER BY g6.total_points DESC"
    )
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=None",
        sql_id,
        response,
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4110(profile, async_cursor):
    """Add negative feedback with prompt_spec=None and a valid sql_id."""
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 "
        "ON p6.id = g6.id ORDER BY g6.total_points ASC, p6.name ASC"
    )
    feedback_content = "print in ascending order of total_points and name"
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=%s",
        sql_id,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=None,
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4111(profile, async_cursor):
    """Add negative feedback with sql_id=None and a valid prompt_spec."""
    prompt = PROMPT
    action = Action.SHOWSQL
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    feedback_content = "print in ascending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        sql_id=None,
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


async def test_4112(profile, async_cursor):
    """Attempt negative feedback with response=None."""
    prompt = PROMPT
    action = Action.SHOWSQL
    feedback_content = "print in ascending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=None feedback_content=%s",
        prompt,
        action,
        feedback_content,
    )
    with pytest.raises(AttributeError) as exc_info:
        await profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            response=None,
            feedback_content=feedback_content,
        )
    assert isinstance(exc_info.value, AttributeError)
    logger.error("%s", str(exc_info.value).splitlines()[0])


async def test_4113(profile, async_cursor):
    """Add negative feedback with feedback_content=None using sql_id."""
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    logger.info(
        "Adding negative feedback with prompt_spec=None sql_id=%s response=%s feedback_content=None",
        sql_id,
        response,
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=None,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt

async def test_4114(profile, async_cursor):
    """Add negative feedback for a non-existent SHOWSQL prompt."""
    prompt = "Adding negative feedback with non existent prompt"
    action = Action.SHOWSQL
    response = (
        "SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 "
        "ON p5.id = g5.id ORDER BY p4.name ASC"
    )
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        feedback_content,
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert response in show_prompt


############################################################## POSITIVE FEEDBACK TESTS
async def test_4115(profile, async_cursor):
    """Add positive feedback using SHOWSQL prompt_spec only."""
    prompt = PROMPT
    action = Action.SHOWSQL
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    await profile.add_positive_feedback(prompt_spec=(prompt, action))
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4116(profile, async_cursor):
    """Add positive feedback using RUNSQL prompt_spec only."""
    prompt = PROMPT
    action = Action.RUNSQL
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    await profile.add_positive_feedback(prompt_spec=(prompt, action))
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4117(profile, async_cursor):
    """Add positive feedback using EXPLAINSQL prompt_spec only."""
    prompt = PROMPT
    action = Action.EXPLAINSQL
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    await profile.add_positive_feedback(prompt_spec=(prompt, action))
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4118(profile, async_cursor):
    """Attempt positive feedback with both prompt_spec and sql_id."""
    prompt = PROMPT
    action = Action.SHOWSQL
    sql_id = SHOWSQL_SQL_ID
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=%s",
        prompt,
        action,
        sql_id,
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        await profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])


async def test_4119(profile, async_cursor):
    """Add positive feedback using SHOWSQL sql_id only."""
    sql_id = SHOWSQL_SQL_ID
    logger.info("Adding positive feedback without prompt_spec using sql_id=%s", sql_id)
    await profile.add_positive_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4120(profile, async_cursor):
    """Add positive feedback using RUNSQL sql_id only."""
    sql_id = RUNSQL_SQL_ID
    logger.info("Adding positive feedback without prompt_spec using sql_id=%s", sql_id)
    await profile.add_positive_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4121(profile, async_cursor):
    """Add positive feedback using EXPLAINSQL sql_id only."""
    sql_id = EXPLAINSQL_SQL_ID
    logger.info("Adding positive feedback without prompt_spec using sql_id=%s", sql_id)
    await profile.add_positive_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4122(profile, async_cursor):
    """Add positive feedback with prompt_spec=None and a valid sql_id."""
    sql_id = SHOWSQL_SQL_ID
    logger.info("Adding positive feedback with prompt_spec=None sql_id=%s", sql_id)
    await profile.add_positive_feedback(
        prompt_spec=None,
        sql_id=sql_id,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


async def test_4123(profile, async_cursor):
    """Add positive feedback with sql_id=None and a valid prompt_spec."""
    prompt = PROMPT
    action = Action.SHOWSQL
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    await profile.add_positive_feedback(
        prompt_spec=(prompt, action),
        sql_id=None,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

async def test_4124(profile, async_cursor):
    """Attempt positive feedback for a non-existent SHOWSQL prompt."""
    prompt = "Adding positive feedback with non existent prompt"
    action = Action.SHOWSQL
    logger.info(
        "Adding positive feedback for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        await profile.add_positive_feedback(prompt_spec=(prompt, action))
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

############################################################## DELETE FEEDBACK TESTS
async def test_4125(profile, async_cursor):
    """Delete feedback by prompt_spec after adding positive SHOWSQL feedback."""
    prompt = PROMPT
    action = Action.SHOWSQL
    logger.info(
        "Adding positive feedback before delete for prompt=%s action=%s",
        prompt,
        action,
    )
    await profile.add_positive_feedback(
        prompt_spec=(prompt, action),
    )
    await _log_feedback_vecindex_rows(profile)

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    await profile.delete_feedback(
        prompt_spec=(prompt, action),
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4126(profile, async_cursor):
    """Delete feedback by RUNSQL sql_id after adding negative feedback with sql_id."""
    sql_id = RUNSQL_SQL_ID
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    logger.info(
        "Adding negative feedback before delete with prompt_spec=None sql_id=%s response=%s feedback_content=%s",
        sql_id,
        response,
        "Feedback prior to delete",
    )
    await profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content="Feedback prior to delete",
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback using sql_id=%s", sql_id)
    await profile.delete_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4127(profile, async_cursor):
    """Delete feedback by prompt_spec after adding positive EXPLAINSQL feedback."""
    prompt = PROMPT
    action = Action.EXPLAINSQL
    logger.info(
        "Adding positive feedback before delete for prompt=%s action=%s",
        prompt,
        action,
    )
    await profile.add_positive_feedback(
        prompt_spec=(prompt, action),
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    await profile.delete_feedback(
        prompt_spec=(prompt, action),
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4128(profile, async_cursor):
    """Delete SHOWSQL feedback by sql_id after adding negative prompt-based feedback."""
    prompt = PROMPT
    action = Action.SHOWSQL
    sql_id = SHOWSQL_SQL_ID
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    logger.info(
        "Adding negative feedback before delete for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        "Feedback prior to delete",
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content="Feedback prior to delete",
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback using sql_id=%s", sql_id)
    await profile.delete_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4129(profile, async_cursor):
    """Delete RUNSQL feedback by sql_id after adding negative prompt-based feedback."""
    prompt = PROMPT
    action = Action.RUNSQL
    sql_id = RUNSQL_SQL_ID
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    logger.info(
        "Adding negative feedback before delete for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        "Feedback prior to delete",
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content="Feedback prior to delete",
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback using sql_id=%s", sql_id)
    await profile.delete_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4130(profile, async_cursor):
    """Delete EXPLAINSQL feedback by sql_id after adding negative prompt-based feedback."""
    prompt = PROMPT
    action = Action.EXPLAINSQL
    sql_id = EXPLAINSQL_SQL_ID
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g "
        "ON p.id = g.id ORDER BY g.total_points DESC"
    )
    logger.info(
        "Adding negative feedback before delete for prompt=%s action=%s sql_id=None response=%s feedback_content=%s",
        prompt,
        action,
        response,
        "Feedback prior to delete",
    )
    await profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content="Feedback prior to delete",
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback using sql_id=%s", sql_id)
    await profile.delete_feedback(sql_id=sql_id)
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4131(profile, async_cursor):
    """Delete feedback with sql_id=None and a valid prompt_spec."""
    prompt = PROMPT
    action = Action.SHOWSQL
    logger.info(
        "Adding positive feedback before delete for prompt=%s action=%s sql_id=None",
        prompt,
        action,
    )
    await profile.add_positive_feedback(
        prompt_spec=(prompt, action),
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info(
        "Deleting feedback for prompt=%s action=%s with sql_id=None",
        prompt,
        action,
    )
    await profile.delete_feedback(
        prompt_spec=(prompt, action),
        sql_id=None,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4132(profile, async_cursor):
    """Delete feedback with prompt_spec=None and a valid sql_id."""
    sql_id = SHOWSQL_SQL_ID
    logger.info(
        "Adding positive feedback before delete without prompt_spec using sql_id=%s",
        sql_id,
    )
    await profile.add_positive_feedback(
        sql_id=sql_id,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Deleting feedback with prompt_spec=None using sql_id=%s", sql_id)
    await profile.delete_feedback(
        prompt_spec=None,
        sql_id=sql_id,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = await profile.show_prompt(PROMPT)
    logger.info("show_prompt response: %s", show_prompt)
    assert show_prompt.count(PROMPT) == 1


async def test_4133(profile, async_cursor):
    """Attempt delete_feedback with both prompt_spec and sql_id."""
    prompt = PROMPT
    action = Action.SHOWSQL
    sql_id = SHOWSQL_SQL_ID
    logger.info(
        "Adding positive feedback before conflicting delete without prompt_spec using sql_id=%s",
        sql_id,
    )
    await profile.add_positive_feedback(
        sql_id=sql_id,
    )
    await _log_feedback_vecindex_rows(profile)
    logger.info(
        "Deleting feedback for prompt=%s action=%s sql_id=%s",
        prompt,
        action,
        sql_id,
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        await profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])
