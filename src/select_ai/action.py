from enum import StrEnum

__all__ = ["Action"]


class Action(StrEnum):
    """Supported Select AI actions"""

    RUNSQL = "runsql"
    SHOWSQL = "showsql"
    EXPLAINSQL = "explainsql"
    NARRATE = "narrate"
    CHAT = "chat"
    SHOWPROMPT = "showprompt"
    EMBEDDING = "embedding"
    SUMMARIZE = "summarize"
    FEEDBACK = "feedback"
