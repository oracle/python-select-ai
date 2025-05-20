import collections
import json
from dataclasses import dataclass
from typing import Optional

from select_ai._base import SelectAIDataClass

__all__ = ["Conversation", "ConversationAttributes"]


Conversation = collections.namedtuple(
    "Conversation", field_names=["conversation_id", "attributes"]
)


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
