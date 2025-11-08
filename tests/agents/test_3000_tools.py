# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""
3000 - Module for testing select_ai agent tools
"""

import uuid

import pytest
import select_ai
from select_ai.agent import Tool

PYSAI_3000_PROFILE_NAME = f"PYSAI_3000_{uuid.uuid4().hex.upper()}"
PYSAI_3000_SQL_TOOL_NAME = f"PYSAI_3000_SQL_TOOL_{uuid.uuid4().hex.upper()}"
PYSAI_3000_SQL_TOOL_DESCRIPTION = f"SQL Tool for Python 3000"

PYSAI_3000_RAG_PROFILE_NAME = f"PYSAI_3000_RAG_{uuid.uuid4().hex.upper()}"
PYSAI_3000_RAG_VECTOR_INDEX_NAME = (
    f"PYSAI_3000_RAG_VECTOR_{uuid.uuid4().hex.upper()}"
)
PYSAI_3000_RAG_TOOL_NAME = f"PYSAI_3000_RAG_TOOL_{uuid.uuid4().hex.upper()}"
PYSAI_3000_RAG_TOOL_DESCRIPTION = f"RAG Tool for Python 3000"

PYSAI_3000_PL_SQL_TOOL_NAME = (
    f"PYSAI_3000_PL_SQL_TOOL_{uuid.uuid4().hex.upper()}"
)
PYSAI_3000_PL_SQL_TOOL_DESCRIPTION = f"PL/SQL Tool for Python 3000"
PYSAI_3000_PL_SQL_FUNC_NAME = (
    f"PYSAI_3000_PL_SQL_FUNC_{uuid.uuid4().hex.upper()}"
)


@pytest.fixture(scope="module")
def python_gen_ai_profile(profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_3000_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def python_gen_rag_ai_profile(rag_profile_attributes):
    profile = select_ai.Profile(
        profile_name=PYSAI_3000_RAG_PROFILE_NAME,
        description="OCI GENAI Profile",
        attributes=rag_profile_attributes,
    )
    yield profile
    profile.delete(force=True)


@pytest.fixture(scope="module")
def sql_tool(python_gen_ai_profile):
    sql_tool = select_ai.agent.Tool.create_sql_tool(
        tool_name=PYSAI_3000_SQL_TOOL_NAME,
        description=PYSAI_3000_SQL_TOOL_DESCRIPTION,
        profile_name=PYSAI_3000_PROFILE_NAME,
        replace=True,
    )
    yield sql_tool
    sql_tool.delete(force=True)


@pytest.fixture(scope="module")
def vector_index(vector_index_attributes, python_gen_rag_ai_profile):
    vector_index = select_ai.VectorIndex(
        index_name=PYSAI_3000_RAG_VECTOR_INDEX_NAME,
        attributes=vector_index_attributes,
        description="Test vector index",
        profile=python_gen_rag_ai_profile,
    )
    vector_index.create(replace=True)
    yield vector_index
    vector_index.delete(force=True)


@pytest.fixture(scope="module")
def rag_tool(vector_index):
    sql_tool = select_ai.agent.Tool.create_rag_tool(
        tool_name=PYSAI_3000_RAG_TOOL_NAME,
        description=PYSAI_3000_RAG_TOOL_DESCRIPTION,
        profile_name=PYSAI_3000_RAG_PROFILE_NAME,
        replace=True,
    )
    yield sql_tool
    sql_tool.delete(force=True)


@pytest.fixture(scope="module")
def pl_sql_function():
    create_function = f"""
    CREATE OR REPLACE FUNCTION {PYSAI_3000_PL_SQL_FUNC_NAME} (p_birth_date IN DATE)
    RETURN NUMBER
    IS
      v_age NUMBER;
    BEGIN
      -- Calculate the difference in years
      v_age := TRUNC(MONTHS_BETWEEN(SYSDATE, p_birth_date) / 12);

      RETURN v_age;
    END CALCULATE_AGE;
    """
    with select_ai.cursor() as cr:
        cr.execute(create_function)
    yield create_function
    with select_ai.cursor() as cr:
        cr.execute(f"DROP FUNCTION {PYSAI_3000_PL_SQL_FUNC_NAME}")


@pytest.fixture(scope="module")
def pl_sql_tool(pl_sql_function):
    pl_sql_tool = select_ai.agent.Tool.create_pl_sql_tool(
        tool_name=PYSAI_3000_PL_SQL_TOOL_NAME,
        function=PYSAI_3000_PL_SQL_FUNC_NAME,
        description=PYSAI_3000_PL_SQL_TOOL_DESCRIPTION,
    )
    yield pl_sql_tool
    pl_sql_tool.delete(force=True)


def test_3000(sql_tool):
    """test SQL tool creation and parameter validation"""
    assert (
        sql_tool.attributes.tool_params.profile_name == PYSAI_3000_PROFILE_NAME
    )
    assert sql_tool.tool_name == PYSAI_3000_SQL_TOOL_NAME
    assert sql_tool.description == PYSAI_3000_SQL_TOOL_DESCRIPTION
    assert isinstance(
        sql_tool.attributes.tool_params, select_ai.agent.SQLToolParams
    )


def test_3001(rag_tool):
    """test RAG tool creation and parameter validation"""
    assert (
        rag_tool.attributes.tool_params.profile_name
        == PYSAI_3000_RAG_PROFILE_NAME
    )
    assert rag_tool.tool_name == PYSAI_3000_RAG_TOOL_NAME
    assert rag_tool.description == PYSAI_3000_RAG_TOOL_DESCRIPTION
    assert isinstance(
        rag_tool.attributes.tool_params, select_ai.agent.RAGToolParams
    )


def test_3002(pl_sql_tool):
    """test PL SQL tool creation and parameter validation"""
    assert pl_sql_tool.tool_name == PYSAI_3000_PL_SQL_TOOL_NAME
    assert pl_sql_tool.description == PYSAI_3000_PL_SQL_TOOL_DESCRIPTION
    assert pl_sql_tool.attributes.function == PYSAI_3000_PL_SQL_FUNC_NAME


def test_3003():
    """list tools"""
    tools = list(select_ai.agent.Tool.list())
    tool_names = set(tool.tool_name for tool in tools)
    assert PYSAI_3000_RAG_TOOL_NAME in tool_names
    assert PYSAI_3000_SQL_TOOL_NAME in tool_names
    assert PYSAI_3000_PL_SQL_TOOL_NAME in tool_names


def test_3004():
    """list tools matching a REGEX pattern"""
    tools = list(select_ai.agent.Tool.list(tool_name_pattern="^PYSAI_3000"))
    tool_names = set(tool.tool_name for tool in tools)
    assert PYSAI_3000_RAG_TOOL_NAME in tool_names
    assert PYSAI_3000_SQL_TOOL_NAME in tool_names
    assert PYSAI_3000_PL_SQL_TOOL_NAME in tool_names


def test_3005():
    """fetch tool"""
    sql_tool = select_ai.agent.Tool.fetch(tool_name=PYSAI_3000_SQL_TOOL_NAME)
    assert sql_tool.tool_name == PYSAI_3000_SQL_TOOL_NAME
    assert sql_tool.description == PYSAI_3000_SQL_TOOL_DESCRIPTION
    assert isinstance(
        sql_tool.attributes.tool_params, select_ai.agent.SQLToolParams
    )
