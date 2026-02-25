# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
4000 - Sync Profile feedback API tests
"""
import logging
import os
import uuid

import oracledb
import pytest
import select_ai
from select_ai.action import Action

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_dcai_feedback_test.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

DUMMY_PROMPT = "dummy Prompt"

# Logging
logger = logging.getLogger(__name__)


def _assert_db_error(exc_info, expected_code):
    assert isinstance(exc_info.value, oracledb.DatabaseError)
    (error,) = exc_info.value.args
    assert error.code == expected_code
    return error


PROFILE_NAME = f"PYSAI_4000_{uuid.uuid4().hex.upper()}"
PROFILE_DESCRIPTION = "OCI Gen AI Test Profile"

# -----------------------------------------------------------------------------
# Setup for feedback tests
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def profile(oci_credential, oci_compartment_id, test_env):
    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        description=PROFILE_DESCRIPTION,
        replace=True,
        attributes=select_ai.ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=[
                {"owner": test_env.test_user, "name": "gymnast"},
                {"owner": test_env.test_user, "name": "people"},
            ],
            provider=select_ai.OCIGenAIProvider(
                oci_compartment_id=oci_compartment_id,
                oci_apiformat="GENERIC",
            ),
        ),
    )

    yield profile
    profile.delete(force=True)


############################################### NEGATIVE FEEDBACK TESTS

def test_4001(profile):
    """CASE : Negative feedback test with SHOWSQL """
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id "
        "ORDER BY g1.total_points DESC"
    )
    feedback_content = "print in descending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s", prompt, action
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4002(profile):
    """CASE : Negative feedback test with EXPLAINSQL """
    prompt = "Total points of each gymnasts"
    action = Action.EXPLAINSQL
    response = (
        "SELECT p2.name, g2.total_points FROM people p2 JOIN gymnast g2 ON p2.id = g2.id "
        "ORDER BY g2.total_points ASC"
    )
    feedback_content = "print in ascending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s", prompt, action
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4003(profile):
    """CASE : Negative feedback test with RUNSQL """
    prompt = "Total points of each gymnasts"
    action = Action.RUNSQL
    response = (
        "SELECT p3.name, g3.total_points FROM people p3 JOIN gymnast g3 ON p3.id = g3.id "
        "ORDER BY g3.total_points DESC"
    )
    feedback_content = "print in descending order of total_points"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s", prompt, action
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4004(profile):
    """CASE : Negative feedback test with SHOWSQL ordering by name"""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 ON p5.id = g5.id "
        "ORDER BY p4.name ASC"
    )
    feedback_content = "print in ascending order of name"
    logger.info(
        "Adding negative feedback for prompt=%s action=%s", prompt, action
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4005(profile):
    """CASE : Test with missing response (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    feedback_content = "print in ascending order of name"
    logger.info(
        "Expecting AttributeError when adding negative feedback for prompt=%s action=%s",
        prompt,
        action,
    )
    with pytest.raises(AttributeError) as exc_info:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            feedback_content=feedback_content,
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])


def test_4006(profile):
    """CASE : Test with missing feedback_content (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )
    logger.info(
        "Adding negative feedback without feedback_content for prompt=%s action=%s",
        prompt,
        action,
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4007(profile):
    """CASE : SQL_ID AND SQL_TEXT BOTH ARE GIVEN AS ARGUMENTS"""

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = (
        "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id "
        "ORDER BY g1.total_points DESC"
    )
    feedback_content = "print in descending order of total_points"
    logger.info(
        "Expecting DatabaseError when adding negative feedback with prompt=%s action=%s sql_id=%s",
        prompt,
        action,
        sql_id,
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])


def test_4008(profile):
    """CASE : SQL_ID FOR NEGATIVE FEEDBACK"""

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = (
        "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id "
        "ORDER BY g1.total_points DESC"
    )
    feedback_content = "print in descending order of total_points"
    logger.info("Adding negative feedback for prompt=%s action=%s", prompt, action)

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    logger.info(
        "Expecting DatabaseError when adding negative feedback using sql_id=%s", sql_id
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_negative_feedback(
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content,
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


############################################################## POSITIVE FEEDBACK TESTS

def test_4009(profile):
    """CASE : Positive feedback test with SHOWSQL """
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    logger.info(
        "Expecting DatabaseError when adding positive feedback with missing prompt"
    )
    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" not in show_prompt
    assert "user_prompt" not in show_prompt


def test_4010(profile):
    """CASE : Positive feedback test with RUNSQL """

    prompt = "Total points of each gymnasts"
    action = Action.RUNSQL
    sql_id = "ahgttusrvh9x5"
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" not in show_prompt
    assert "user_prompt" not in show_prompt


def test_4011(profile):
    """CASE : Positive feedback test with EXPLAINSQL """
    prompt = "Total points of each gymnasts"
    action = Action.EXPLAINSQL
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )

    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" not in show_prompt
    assert "user_prompt" not in show_prompt


def test_4012(profile):
    """CASE : SQL_ID AND SQL_TEXT BOTH ARE GIVEN AS ARGUMENT"""

    sql_id = "ahgttusrvh9x5"
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert "sql_query" not in show_prompt
    assert "user_prompt" not in show_prompt


def test_4013(profile):
    """CASE : SQL_TEXT DOES NOT MATCH ANY EXISTING FEEDBACK SQL_TEXT"""

    prompt = "Total number of gymnasts"
    action = Action.SHOWSQL

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])


def test_4014(profile):
    """CASE : SQL_ID DOES NOT MATCH ANY EXISTING FEEDBACK SQL_ID"""

    sql_id = "sql_id_mismatch"

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.add_positive_feedback(sql_id=sql_id)
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])


############################################################## DELETE FEEDBACK TESTS

def test_4015(profile):
    """CASE : Delete feedback test with SHOWSQL """

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id "
        "ORDER BY g6.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4016(profile):
    """CASE : Delete feedback test with RUNSQL """
    prompt = "Total points of each gymnasts"
    action = Action.RUNSQL
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id "
        "ORDER BY g.total_points DESC"
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4017(profile):
    """CASE : Delete feedback test with EXPLAINSQL """
    prompt = "Total points of each gymnasts"
    action = Action.EXPLAINSQL
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id "
        "ORDER BY g.total_points DESC"
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4018(profile):
    """CASE : SQL_ID AND SQL_TEXT EXISTS AND BOTH ARE GIVEN AS ARGUMENT"""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id "
        "ORDER BY g.total_points DESC"
    )
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )
    logger.info("Retrieving prompt via show_prompt for dummy input")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
        )
    _assert_db_error(exc_info, 6550)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt


def test_4019(profile):
    """CASE : SQL_TEXT DOES NOT MATCH ANY EXISTING FEEDBACK SQL_TEXT"""

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = (
        "SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id "
        "ORDER BY g.total_points DESC"
    )

    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
    )

    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response in show_prompt
    assert prompt in show_prompt

    prompt = "Total number of gymnasts"

    with pytest.raises(oracledb.DatabaseError) as exc_info:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
        )
    _assert_db_error(exc_info, 20000)
    logger.error("%s", str(exc_info.value).splitlines()[0])

    prompt = "Total points of each gymnasts"
    logger.info("Deleting feedback for prompt=%s action=%s", prompt, action)
    profile.delete_feedback(prompt_spec=(prompt, action))
    logger.info("Retrieving prompt after deletion to verify removal")
    show_prompt = profile.show_prompt(DUMMY_PROMPT)
    assert response not in show_prompt
    assert prompt not in show_prompt
