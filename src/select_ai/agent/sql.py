# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------


GET_USER_AI_AGENT = """
SELECT a.agent_name, a.description
from USER_AI_AGENTS a
where a.agent_name = :agent_name
"""

GET_USER_AI_AGENT_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_AI_AGENT_ATTRIBUTES
WHERE agent_name = :agent_name
"""

LIST_USER_AI_AGENTS = """
SELECT a.agent_name, a.description
from USER_AI_AGENTS a
where REGEXP_LIKE(a.agent_name, :agent_name_pattern, 'i')
"""

GET_USER_AI_AGENT_TASK = """
SELECT t.task_name, t.description
FROM USER_AI_AGENT_TASKS t
WHERE t.task_name= :task_name
"""

GET_USER_AI_AGENT_TASK_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_AI_AGENT_TASK_ATTRIBUTES
WHERE task_name= :task_name
"""

LIST_USER_AI_AGENT_TASKS = """
SELECT t.task_name, t.description
FROM USER_AI_AGENT_TASKS t
WHERE REGEXP_LIKE(t.task_name, :task_name_pattern, 'i')
"""

GET_USER_AI_TOOL = """
SELECT t.tool_name, t.description
FROM USER_AI_AGENT_TOOLS t
WHERE t.tool_name = :tool_name
"""

GET_USER_AI_AGENT_TOOL_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_AI_AGENT_TOOL_ATTRIBUTES
WHERE tool_name = :tool_name
"""

LIST_USER_AI_AGENT_TOOLS = """
SELECT t.tool_name, t.description
FROM USER_AI_AGENT_TOOLS t
WHERE REGEXP_LIKE(t.tool_name, :tool_name_pattern, 'i')
"""


GET_USER_AI_AGENT_TEAM = """
SELECT t.tool_name, t.description
FROM USER_AI_AGENT_TEAMS t
WHERE t.team_name = :team_name
"""

GET_USER_AI_AGENT_TEAM_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_AI_AGENT_TEAM_ATTRIBUTES
WHERE team_name = :team_name
"""

LIST_USER_AI_AGENT_TEAMS = """
SELECT t.tool_name, t.description
FROM USER_AI_AGENT_TEAMS t
WHERE REGEXP_LIKE(t.team_name, :team_name_pattern, 'i')
"""
