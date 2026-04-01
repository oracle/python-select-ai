# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import pytest

from select_ai.errors import (
    AgentAttributesEmptyError,
    AgentNotFoundError,
    AgentTaskAttributesEmptyError,
    AgentTaskNotFoundError,
    AgentTeamAttributesEmptyError,
    AgentTeamNotFoundError,
    AgentToolAttributesEmptyError,
    AgentToolNotFoundError,
    ConversationNotFoundError,
    DatabaseNotConnectedError,
    InvalidSQLError,
    ProfileAttributesEmptyError,
    ProfileExistsError,
    ProfileNotFoundError,
    VectorIndexNotFoundError,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            DatabaseNotConnectedError(),
            "Not connected to the Database. Use select_ai.connect() or "
            "select_ai.async_connect() to establish connection",
        ),
        (
            ConversationNotFoundError("conv-1"),
            "Conversation with id conv-1 not found",
        ),
        (ProfileNotFoundError("demo"), "Profile demo not found"),
        (
            ProfileExistsError("demo"),
            "Profile demo already exists. Use either replace=True or merge=True",
        ),
        (
            ProfileAttributesEmptyError("demo"),
            "Profile demo attributes empty in the database. ",
        ),
        (VectorIndexNotFoundError("idx"), "VectorIndex idx not found"),
        (
            VectorIndexNotFoundError("idx", "demo"),
            "VectorIndex idx not found for profile demo",
        ),
        (AgentNotFoundError("agent"), "Agent agent not found"),
        (
            AgentAttributesEmptyError("agent"),
            "Agent agent attributes empty in the database.",
        ),
        (AgentTaskNotFoundError("task"), "Agent Task task not found"),
        (
            AgentTaskAttributesEmptyError("task"),
            "Agent Task task attributes empty in the database.",
        ),
        (AgentToolNotFoundError("tool"), "Agent Tool tool not found"),
        (
            AgentToolAttributesEmptyError("tool"),
            "Agent tool tool attributes empty in the database.",
        ),
        (AgentTeamNotFoundError("team"), "Agent Team team not found"),
        (
            AgentTeamAttributesEmptyError("team"),
            "Agent team team attributes empty in the database.",
        ),
        (InvalidSQLError("bad sql"), "bad sql"),
    ],
)
def test_4700_error_messages_are_stable(error, expected):
    assert str(error) == expected

