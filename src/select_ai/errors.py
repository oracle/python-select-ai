# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------


class SelectAIError(Exception):
    """Base class for any SelectAIErrors"""

    pass


class DatabaseNotConnectedError(SelectAIError):
    """Raised when a database is not connected"""

    def __str__(self):
        return (
            "Not connected to the Database. "
            "Use select_ai.connect() or select_ai.async_connect() "
            "to establish connection"
        )


class ConversationNotFoundError(SelectAIError):
    """Conversation not found in the database"""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id

    def __str__(self):
        return f"Conversation with id {self.conversation_id} not found"


class ProfileNotFoundError(SelectAIError):
    """Profile not found in the database"""

    def __init__(self, profile_name: str):
        self.profile_name = profile_name

    def __str__(self):
        return f"Profile {self.profile_name} not found"


class ProfileExistsError(SelectAIError):
    """Profile already exists in the database"""

    def __init__(self, profile_name: str):
        self.profile_name = profile_name

    def __str__(self):
        return (
            f"Profile {self.profile_name} already exists. "
            f"Use either replace=True or merge=True"
        )


class VectorIndexNotFoundError(SelectAIError):
    """VectorIndex not found in the database"""

    def __init__(self, index_name: str, profile_name: str = None):
        self.index_name = index_name
        self.profile_name = profile_name

    def __str__(self):
        if self.profile_name:
            return (
                f"VectorIndex {self.index_name} "
                f"not found for profile {self.profile_name}"
            )
        else:
            return f"VectorIndex {self.index_name} not found"


class AgentNotFoundError(SelectAIError):
    """Agent not found in the database"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def __str__(self):
        return f"Agent {self.agent_name} not found"


class AgentTaskNotFoundError(SelectAIError):
    """Agent task not found in the database"""

    def __init__(self, task_name: str):
        self.task_name = task_name

    def __str__(self):
        return f"Agent Task {self.task_name} not found"


class AgentToolNotFoundError(SelectAIError):
    """Agent tool not found in the database"""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name

    def __str__(self):
        return f"Agent Tool {self.tool_name} not found"


class AgentTeamNotFoundError(SelectAIError):
    """Agent team not found in the database"""

    def __init__(self, team_name: str):
        self.team_name = team_name

    def __str__(self):
        return f"Agent Team {self.team_name} not found"
