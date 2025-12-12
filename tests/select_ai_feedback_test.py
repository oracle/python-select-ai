import logging
import os
import select_ai
from select_ai.action import Action
import oracledb
import pytest
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROFILE_NAME = "PYSAI_TEST_FEEDBACK_PROFILE"
PROFILE_DESCRIPTION = "OCI Gen AI Test Profile"

@pytest.fixture(scope="module")
def profile(oci_credential, oci_compartment_id, test_env):
    profile = select_ai.Profile(
        profile_name=PROFILE_NAME,
        description=PROFILE_DESCRIPTION,
        attributes=select_ai.ProfileAttributes(
            credential_name=oci_credential["credential_name"],
            object_list=[{"owner": test_env.test_user, "name": "gymnast"}, {"owner": test_env.test_user, "name": "people"}],
            provider=select_ai.OCIGenAIProvider(
                oci_compartment_id=oci_compartment_id, oci_apiformat="GENERIC"
            ),
        ),
    )
    with select_ai.cursor() as cr:
        cr.execute("""
        BEGIN
           dbms_cloud_ai.set_profile('PYSAI_TEST_FEEDBACK_PROFILE');
        END;
        """)
        cr.execute("select ai showsql Total points of each gymnasts")
        cr.execute("select ai runsql Total points of each gymnasts")
        cr.execute("select ai explainsql Total points of each gymnasts")

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
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Failed to add negative feedback for SHOWSQL: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback for SHOWSQL")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_valid_input_explainsql(profile):
    """Valid input: Test with valid prompt_spec, sql_id, response, and feedback_content."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    response = 'SELECT p2.name, g2.total_points FROM people p2 JOIN gymnast g2 ON p2.id = g2.id ORDER BY g2.total_points ASC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of total_points"
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Failed to add negative feedback for EXPLAINSQL: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback for EXPLAINSQL")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_valid_input_runsql(profile):
    """Valid input: Test with valid prompt_spec, sql_id, response, and feedback_content."""
    prompt = 'Total points of each gymnasts'
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    response = 'SELECT p3.name, g3.total_points FROM people p3 JOIN gymnast g3 ON p3.id = g3.id ORDER BY g3.total_points DESC'  # Valid SQL on your tables
    feedback_content = "print in descending order of total_points"
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Failed to add negative feedback for RUNSQL: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback for RUNSQL")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_missing_prompt_spec(profile):

    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p4.name, g4.total_points FROM people p4 JOIN gymnast g4 ON p4.id = g4.id ORDER BY p4.name DESC'  # Valid SQL on your tables
    feedback_content = "print in descending order of name"
    success = False
    try:
        profile.add_negative_feedback(
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Unexpected failure when prompt_spec missing: %s", exc)
    else:
        success = True
        logger.info("Successfully added negative feedback without prompt_spec")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_missing_sql_id(profile):
    
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = 'SELECT p5.name, g5.total_points FROM people p5 JOIN gymnast g5 ON p5.id = g5.id ORDER BY p4.name ASC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of name"
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Unexpected failure when sql_id missing: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback without sql_id")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_missing_response(profile):
    """Missing required parameters: Test with missing response (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    feedback_content = "print in ascending order of name"
    expected_exception = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Negative feedback failed expectedly due to missing response: %s", exc)
        assert "response" in str(exc)
    else:
        logger.info("Negative feedback unexpectedly succeeded without response")

def test_add_negative_feedback_missing_feedback_content(profile):
    """Missing required parameters: Test with missing feedback_content (for negative feedback)."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id ORDER BY g6.total_points DESC'  # Valid SQL on your tables
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response
        )
    except Exception as exc:
        logger.error("Unexpected failure when feedback_content missing: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback without feedback_content")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_empty_prompt_spec(profile):
    """Empty input: Test with empty strings or None values for prompt_spec."""
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p6.name, g6.total_points FROM people p6 JOIN gymnast g6 ON p6.id = g6.id ORDER BY g6.total_points ASC, p6.name ASC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of total_points and name"
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=None,
            sql_id=sql_id,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Unexpected failure when prompt_spec empty: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback with empty prompt_spec")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_empty_sql_id(profile):
    """Empty input: Test with empty strings or None values for sql_id."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  # Valid SQL on your tables
    feedback_content = "print in ascending order of total_points"
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=None,
            response=response,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Unexpected failure when sql_id empty: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback with empty sql_id")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

def test_add_negative_feedback_empty_response(profile):
    """Empty input: Test with empty strings or None values for response."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    feedback_content = "print in ascending order of total_points"
    # Test with None response
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=None,
            feedback_content=feedback_content
        )
    except Exception as exc:
        logger.error("Negative feedback failed expectedly due to empty response: %s", exc)
        assert "response" in str(exc)
    else:
        logger.error("Negative feedback succeeded unexpectedly despite empty response")
        pytest.fail("Expected an error for empty response")


def test_add_negative_feedback_empty_feedback_content(profile):
    """Empty input: Test with empty strings or None values for feedback_content."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  # Valid SQL on your tables
    success = False
    try:
        profile.add_negative_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id,
            response=response,
            feedback_content=None
        )
    except Exception as exc:
        logger.error("Unexpected failure when feedback_content empty: %s", exc)
        raise
    else:
        success = True
        logger.info("Successfully added negative feedback with empty feedback_content")
    assert success
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert response in show_prompt

############################################################## POSITIVE FEEDBACK TESTS 
def test_add_positive_feedback_valid_input_showsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    try:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to add positive feedback for SHOWSQL: %s", exc)
        raise
    logger.info("Successfully added positive feedback for SHOWSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

def test_add_positive_feedback_valid_input_action_runsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id for RUNSQL action."""
    prompt = 'Total points of each gymnasts'
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    try:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to add positive feedback for RUNSQL: %s", exc)
        raise
    logger.info("Successfully added positive feedback for RUNSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

def test_add_positive_feedback_valid_input_action_explainsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id for EXPLAINSQL action."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    try:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to add positive feedback for EXPLAINSQL: %s", exc)
        raise
    logger.info("Successfully added positive feedback for EXPLAINSQL")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

def test_add_positive_feedback_missing_prompt_spec(profile):

    sql_id = "ahgttusrvh9x5"
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL

    try:
        profile.add_positive_feedback(
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Unexpected failure when adding positive feedback without prompt_spec: %s", exc)
        raise
    else:
        logger.info("Positive feedback succeeded without prompt_spec")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

def test_add_positive_feedback_missing_sql_id(profile):

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    try:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action)
        )
    except Exception as exc:
        logger.error("Unexpected failure when adding positive feedback without sql_id: %s", exc)
        raise
    else:
        logger.info("Positive feedback succeeded without sql_id")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

def test_add_positive_feedback_empty_prompt_spec(profile):
    """Empty input: Test with empty strings or None values for prompt_spec."""

    sql_id = "ahgttusrvh9x5"
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    try:
        profile.add_positive_feedback(
            prompt_spec=None,
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Unexpected failure when positive feedback provided empty prompt_spec: %s", exc)
        raise
    else:
        logger.info("Positive feedback succeeded with empty prompt_spec")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt


def test_add_positive_feedback_empty_sql_id(profile):
    """Empty input: Test with empty strings or None values for sql_id."""

    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    try:
        profile.add_positive_feedback(
            prompt_spec=(prompt, action),
            sql_id=None
        )
    except Exception as exc:
        logger.error("Unexpected failure when positive feedback provided empty sql_id: %s", exc)
        raise
    else:
        logger.info("Positive feedback succeeded with empty sql_id")
    logger.info("Checking if show_prompt contains feedback metadata")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert "sql_query" in show_prompt
    assert "user_prompt" in show_prompt

############################################################## DELETE FEEDBACK TESTS
def test_delete_feedback_valid_input_showsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id
    )
    logger.info("Added positive feedback before deleting SHOWSQL feedback")

    delete_success = False
    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to delete feedback for SHOWSQL: %s", exc)
        raise
    else:
        delete_success = True
        logger.info("Successfully deleted feedback for SHOWSQL")
    assert delete_success

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.info("Feedback for SHOWSQL already deleted")
    else:
        logger.info("Repeated delete for SHOWSQL executed without error")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_runsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = "Total points of each gymnasts"
    action = Action.RUNSQL
    sql_id = "6s20ukn8j3p5j"
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id,
        response=response,
        feedback_content="Feedback prior to delete"
    )
    logger.info("Added negative feedback before deleting RUNSQL feedback")

    delete_success = False
    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to delete feedback for RUNSQL: %s", exc)
        raise
    else:
        delete_success = True
        logger.info("Successfully deleted feedback for RUNSQL")
    assert delete_success

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("feedback for RUNSQL has been deleted already")
    else:
        logger.info("Repeated feedback delete for RUNSQL executed unexpectedly")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_explainsql(profile):
    """Valid input: Test with valid prompt_spec and sql_id."""
    prompt = 'Total points of each gymnasts'
    action = Action.EXPLAINSQL
    sql_id = "2a617cynwfm36"
    profile.add_positive_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id
    )
    logger.info("Added positive feedback before delete EXPLAINSQL")

    delete_success = False
    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to delete feedback for EXPLAINSQL: %s", exc)
        raise
    else:
        delete_success = True
        logger.info("Successfully deleted feedback for EXPLAINSQL")
    assert delete_success

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("feedback for EXPLAINSQL has been deleted already")
    else:
        logger.info("Repeated feedback delete for EXPLAINSQL executed unexpectedly")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_valid_input_with_negative_feedback(profile):
    """Valid input: Test with valid prompt_spec and sql_id for negative feedback."""
    prompt = "Total points of each gymnasts"
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"
    response = 'SELECT p.name, g.total_points FROM people p JOIN gymnast g ON p.id = g.id ORDER BY g.total_points DESC'  
    profile.add_negative_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id,
        response=response,
        feedback_content="Feedback prior to delete"
    )
    logger.info("Added negative feedback before delete SHOWSQL")

    delete_success = False
    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Failed to delete feedback for SHOWSQL after negative feedback: %s", exc)
        raise
    else:
        delete_success = True
        logger.info("Successfully deleted feedback for SHOWSQL after negative feedback")
    assert delete_success

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action),
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("feedback for SHOWSQL has been deleted already")
    else:
        logger.info("Repeated feedback delete for SHOWSQL executed unexpectedly")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_missing_prompt_spec(profile):

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "ahgttusrvh9x5"

    profile.add_positive_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id
    )
    logger.info("Added positive feedback before delete without prompt_spec")

    try:
        profile.delete_feedback(
            sql_id=sql_id
        )
    except Exception as exc:
        logger.error("Unexpected failure when deleting without prompt_spec: %s", exc)
        raise
    else:
        logger.info("Successfully deleted feedback without prompt_spec")

    try:
        profile.delete_feedback(
            sql_id=sql_id
        )
    except Exception as exc:
        logger.info("Feedback without prompt_spec already deleted")
    else:
        logger.info("Repeated delete without prompt_spec executed without error")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1

def test_delete_feedback_missing_sql_id(profile):

    prompt = 'Total points of each gymnasts'
    action = Action.SHOWSQL
    sql_id = "1v1z68ra6r9zf"

    profile.add_positive_feedback(
        prompt_spec=(prompt, action),
        sql_id=sql_id
    )
    logger.info("Added positive feedback before delete without sql_id")

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action)
        )
    except Exception as exc:
        logger.error("Unexpected failure when deleting without sql_id: %s", exc)
        raise
    else:
        logger.info("Successfully deleted feedback without sql_id")

    try:
        profile.delete_feedback(
            prompt_spec=(prompt, action)
        )
    except Exception as exc:
        logger.info("Feedback without sql_id already deleted")
    else:
        logger.info("Repeated delete without sql_id executed without error")

    logger.info("Checking absence of feedback in show_prompt")
    show_prompt = profile.show_prompt('Total points of each gymnasts')
    assert show_prompt.count('Total points of each gymnasts') == 1
