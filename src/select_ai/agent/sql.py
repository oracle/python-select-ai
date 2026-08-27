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

GET_USER_AI_AGENT_TOOL = """
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
SELECT t.agent_team_name as team_name, t.description
FROM USER_AI_AGENT_TEAMS t
WHERE t.agent_team_name = :team_name
"""


GET_USER_AI_AGENT_TEAM_ATTRIBUTES = """
SELECT attribute_name, attribute_value
FROM USER_AI_AGENT_TEAM_ATTRIBUTES
WHERE agent_team_name = :team_name
"""


LIST_USER_AI_AGENT_TEAMS = """
SELECT t.AGENT_TEAM_NAME as team_name, description
FROM USER_AI_AGENT_TEAMS t
WHERE REGEXP_LIKE(t.AGENT_TEAM_NAME, :team_name_pattern, 'i')
"""


LIST_USER_AI_AGENT_TEAM_HISTORY = """
SELECT team_exec_id, team_name, state, start_date, end_date, conversation_id,
       params
FROM user_ai_agent_team_history
WHERE (:team_name IS NULL OR team_name = :team_name)
  AND (:team_exec_id IS NULL OR team_exec_id = :team_exec_id)
ORDER BY start_date DESC NULLS LAST
"""


LIST_USER_AI_AGENT_TASK_HISTORY = """
SELECT team_exec_id, team_name, task_order, agent_name, task_name,
       conversation_params, input, result, state, start_date, end_date
FROM user_ai_agent_task_history
WHERE (:team_name IS NULL OR team_name = :team_name)
  AND (:task_name IS NULL OR task_name = :task_name)
  AND (:agent_name IS NULL OR agent_name = :agent_name)
  AND (:team_exec_id IS NULL OR team_exec_id = :team_exec_id)
ORDER BY start_date DESC NULLS LAST
"""


LIST_USER_AI_AGENT_TOOL_HISTORY = """
SELECT invocation_id, team_exec_id, task_order, tool_name, agent_name,
       task_name, start_date, end_date, input, output, tool_output
FROM user_ai_agent_tool_history
WHERE (:tool_name IS NULL OR tool_name = :tool_name)
  AND (:task_name IS NULL OR task_name = :task_name)
  AND (:agent_name IS NULL OR agent_name = :agent_name)
  AND (:team_exec_id IS NULL OR team_exec_id = :team_exec_id)
ORDER BY start_date DESC NULLS LAST
"""
