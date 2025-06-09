import json
from dataclasses import dataclass
from typing import Optional

from select_ai._abc import SelectAIDataClass

__all__ = ["Conversation", "ConversationAttributes"]


@dataclass
class Conversation(SelectAIDataClass):
    """A container class to store Conversation id and attributes"""

    conversation_id: str
    attributes: "ConversationAttributes"


@dataclass
class ConversationAttributes(SelectAIDataClass):
    """Conversation Attributes"""

    title: Optional[str] = "New Conversation"
    description: Optional[str] = None
    retention_days: Optional[int] = 7
    # conversation_length: Optional[int] = 10
