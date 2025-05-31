import collections
import json
from dataclasses import dataclass
from typing import NamedTuple, Optional

from select_ai._base import SelectAIDataClass

__all__ = ["Conversation", "ConversationAttributes"]


class Conversation(NamedTuple):
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

    def json(self):
        attributes = {}
        for k, v in self.__dict__.items():
            if v:
                attributes[k] = v
        return json.dumps(attributes)
