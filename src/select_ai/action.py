# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from select_ai._enums import StrEnum

__all__ = ["Action"]


class Action(StrEnum):
    """Supported Select AI actions"""

    RUNSQL = "runsql"
    SHOWSQL = "showsql"
    EXPLAINSQL = "explainsql"
    NARRATE = "narrate"
    CHAT = "chat"
    SHOWPROMPT = "showprompt"
    FEEDBACK = "feedback"
    SUMMARIZE = "summarize"
