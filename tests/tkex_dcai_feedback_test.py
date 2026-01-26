# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3000 - Profile feedback API tests
"""
import logging
import select_ai
from select_ai.action import Action
import pytest
import uuid
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOG_FILE = os.path.join(PROJECT_ROOT, "log", "tkex_dcai_feedback_test.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Logging
root = logging.getLogger()
root.setLevel(logging.INFO)
for h in root.handlers[:]:
    root.removeHandler(h)
fh = logging.FileHandler(LOG_FILE, mode="w")
fh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
root.addHandler(fh)
logger = logging.getLogger()


PROFILE_NAME = f"PYSAI_3000_{uuid.uuid4().hex.upper()}"
PROFILE_DESCRIPTION = "OCI Gen AI Test Profile"

# -----------------------------------------------------------------------------
# Per-test logging
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def log_test_name(request):
    logger.info(f"--- Starting test: {request.function.__name__} ---")
    yield
    logger.info(f"--- Finished test: {request.function.__name__} ---")

# -----------------------------------------------------------------------------
# Setup for feedback tests
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def profile(oci_credential, oci_compartment_id, test_env, cursor):
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
    cursor.execute(
    f"""
    BEGIN
        dbms_cloud_ai.set_profile('{PROFILE_NAME}');
    END;
    """
    )
    cursor.execute("select ai showsql Total points of each gymnasts")
    cursor.execute("select ai runsql Total points of each gymnasts")
    cursor.execute("select ai explainsql Total points of each gymnasts")

    yield profile
    profile.delete(force=True)


############################################### NEGATIVE FEEDBACK TESTS
def test_add_negative_feedback_valid_input_showsql(profile):
    """Valid input: Test with valid prompt_spec, sql_id, response, and feedback_content."""
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id ORDER BY g1.total_points DESC"  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback for SHOWSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output for SHOWSQL")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved for SHOWSQL")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action),
    )

def test_add_negative_feedback_valid_input_explainsql(profile):
    """Valid input: Test with valid prompt_spec, sql_id, response, and feedback_content."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    response = 'SELECT p2.name, g2.total_points FROM people p2 JOIN gymnast g2 ON p2.id = g2.id ORDER BY g2.total_points ASC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of total_points"
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback for EXPLAINSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output for EXPLAINSQL")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved for EXPLAINSQL")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_negative_feedback_valid_input_runsql(profile):
    """Valid input: Test with valid prompt_spec, sql_id, response, and feedback_content."""
    prompt = 'Total points of each gymnasts'
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    response = 'SELECT p3.name, g3.total_points FROM people p3 JOIN gymnast g3 ON p3.id = g3.id ORDER BY g3.total_points DESC'  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback for RUNSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output for RUNSQL")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved for RUNSQL")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_negative_feedback_with_sql_id(profile):
    prompt = "Total points of each gymnasts"
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p4.name, g4.total_points FROM people p4 JOIN gymnast g4 ON p4.id = g4.id ORDER BY p4.name DESC'  # Valid SQL on your tables
    feedback_content = "print in descending order of name"
    profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback without prompt_spec")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output without prompt_spec")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved without prompt_spec")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        sql_id=sql_id
    )

def test_add_negative_feedback_with_sql_text(profile):
    
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = 'SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 ON p5.id = g5.id ORDER BY p4.name ASC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of name"
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback without sql_id")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output without sql_id")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved without sql_id")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_negative_feedback_missing_response(profile):
    """Missing required parameters: Test with missing response (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    feedback_content = "print in ascending order of name"
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            feedback_content=feedback_content
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_negative_feedback_missing_feedback_content(profile):
    """Missing required parameters: Test with missing feedback_content (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id ORDER BY g6.total_points DESC'  # Valid SQL on your tables
    profile.add_negative_feedback(
        sql_id=sql_id,
        response=response
    )
    logger.info("Successfully added negative feedback without feedback_content")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved without feedback_content")
    assert response in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_negative_feedback_with_sql_id_and_sql_text(profile):

    """CASE : SQL_ID AND SQL_TEXT EXISTS AND BOTH ARE GIVEN AS ARGUMENTS"""

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id ORDER BY g1.total_points DESC"  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_negative_feedback_with_non_existent_sql_text(profile):

    """CASE : SQL_TEXT DOES NOT MATCH ANY EXISTING FEEDBACK SQL_TEXT"""

    prompt = 'Total number of gymnasts'
    action = Action.SHOWSQL
    response = "SELECT count(*) from gymnast g1"  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            response=response,
            feedback_content=feedback_content
    )
    logger.info("Successfully added negative feedback")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt(prompt)
    assert response in show_prompt
    logger.info("show_prompt output retrieved")
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_negative_feedback_with_sql_id_mismatch(profile):

    """CASE : SQL_ID DOES NOT MATCH ANY EXISTING FEEDBACK SQL_ID"""

    sql_id = "random"
    response = "SELECT p1.name, g1.total_points FROM people p1 JOIN gymnast g1 ON p1.id = g1.id ORDER BY g1.total_points DESC"  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_negative_feedback(
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])


############################################################## POSITIVE FEEDBACK TESTS 
def test_add_positive_feedback_valid_input_showsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully added positive feedback for SHOWSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output after positive SHOWSQL feedback")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved after positive SHOWSQL feedback")
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
            prompt_spec=(prompt, action)
        )

def test_add_positive_feedback_valid_input_action_runsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id for RUNSQL action."""
    prompt = 'Total points of each gymnasts'
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    profile.add_positive_feedback(
        sql_id=sql_id
    )
    logger.info("Successfully added positive feedback for RUNSQL")

    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output after positive RUNSQL feedback")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved after positive RUNSQL feedback")
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_positive_feedback_valid_input_action_explainsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id for EXPLAINSQL action."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully added positive feedback for EXPLAINSQL")

    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output after positive EXPLAINSQL feedback")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved after positive EXPLAINSQL feedback")
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
            prompt_spec=(prompt, action)
    )

def test_add_positive_feedback_with_sql_id(profile):

    sql_id = "ahgttusrvh9x5"
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL

    profile.add_positive_feedback(
        sql_id=sql_id
    )
    logger.info("Positive feedback succeeded without prompt_spec")

    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output after positive feedback without prompt_spec")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved after positive feedback without prompt_spec")
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        sql_id=sql_id
    )

def test_add_positive_feedback_with_sql_text(profile):

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Positive feedback succeeded without sql_id")

    logger.info("Checking if show_prompt contains feedback metadata")
    logger.info("Fetching show_prompt output after positive feedback without sql_id")
    show_prompt = profile.show_prompt(prompt)
    logger.info("show_prompt output retrieved after positive feedback without sql_id")
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt
    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )

def test_add_positive_feedback_with_sql_text_and_sql_id(profile):

    """CASE : SQL_ID AND SQL_TEXT EXISTS AND BOTH ARE GIVEN AS ARGUMENT"""

    sql_id = "ahgttusrvh9x5"
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL

    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_positive_feedback_with_sql_text_mismatch(profile):

    """CASE : SQL_TEXT DOES NOT MATCH ANY EXISTING FEEDBACK SQL_TEXT"""

    prompt = 'Total number of gymnasts'
    action = Action.SHOWSQL

    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action)
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_positive_feedback_with_sql_id_mismatch(profile):

    """CASE : SQL_ID DOES NOT MATCH ANY EXISTING FEEDBACK SQL_ID"""

    sql_id = "sql_id_mismatch"

    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.add_positive_feedback(
            sql_id=sql_id
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

############################################################## DELETE FEEDBACK TESTS
def test_delete_feedback_valid_input_showsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Added positive feedback before deleting SHOWSQL feedback")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully deleted feedback for SHOWSQL")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_runsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = "Total points of each gymnasts"
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        response=response,
        feedback_content="Feedback prior to delete"
    )
    logger.info("Added negative feedback before deleting RUNSQL feedback")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        sql_id=sql_id
    )
    logger.info("Successfully deleted feedback for RUNSQL")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_explainsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Added positive feedback before delete EXPLAINSQL")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully deleted feedback for EXPLAINSQL")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_with_negative_feedback(profile):
    """Valid input: Test with valid prompt_spec and sql_id for negative feedback."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  
    profile.add_negative_feedback(
        sql_id=sql_id,
        response=response,
        feedback_content="Feedback prior to delete"
    )
    logger.info("Added negative feedback before delete SHOWSQL")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully deleted feedback for SHOWSQL after negative feedback")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_with_sql_id(profile):

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"

    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Added positive feedback before delete without prompt_spec")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        sql_id=sql_id
    )
    logger.info("Successfully deleted feedback without prompt_spec")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_with_sql_text(profile):

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"

    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Added positive feedback before delete without sql_id")

    logger.info("Deleting feedback to clean up test state")
    profile.delete_feedback(
        prompt_spec=(prompt, action)
    )
    logger.info("Successfully deleted feedback without sql_id")
    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt(prompt)
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_add_delete_feedback_with_sql_id_and_sql_text(profile):

    """CASE : SQL_ID AND SQL_TEXT EXISTS AND BOTH ARE GIVEN AS ARGUMENT"""

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"

    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )

    logger.info("Attempting delete feedback with SQL_ID AND SQL_TEXT")
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_delete_feedback_with_sql_text_mismatch(profile):

    """CASE : SQL_TEXT DOES NOT MATCH ANY EXISTING FEEDBACK SQL_TEXT"""

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL

    profile.add_positive_feedback(
        prompt_spec=(prompt, action)
    )

    prompt = 'Total number of gymnasts'

    logger.info("Attempting delete feedback with mismatched SQL Text")
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.delete_feedback(
            prompt_spec=(prompt, action)
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])

def test_add_delete_feedback_with_sql_id_mismatch(profile):

    """CASE : SQL_ID DOES NOT MATCH ANY EXISTING FEEDBACK SQL_ID"""

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"

    profile.add_positive_feedback(
        sql_id=sql_id
    )

    sql_id = "random"

    logger.info("Attempting delete feedback with mismatched SQL ID")
    logger.info("Expecting exception when invoking feedback API")
    with pytest.raises(Exception) as exc_info:
        profile.delete_feedback(
            sql_id=sql_id
        )
    logger.error("%s", str(exc_info.value).splitlines()[0])
