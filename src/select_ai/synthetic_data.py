import json
from dataclasses import dataclass
from typing import List, Mapping, Optional

from select_ai._base import SelectAIDataClass


@dataclass
class SyntheticDataParams(SelectAIDataClass):

    sample_rows: Optional[int] = None
    table_statistics: Optional[bool] = False
    priority: Optional[str] = "HIGH"
    comments: Optional[bool] = False

    def dict(self):
        attributes = {}
        for k, v in self.__dict__.items():
            if v:
                attributes[k] = v
        return attributes

    def json(self):
        return json.dumps(self.dict())


@dataclass
class SyntheticDataAttributes(SelectAIDataClass):

    object_name: Optional[str] = None
    owner_name: Optional[str] = None
    record_count: Optional[int] = None
    user_prompt: Optional[str] = None
    params: Optional[SyntheticDataParams] = None
    object_list: Optional[List[Mapping]] = None

    def dict(self):
        attributes = {}
        for k, v in self.__dict__.items():
            if v:
                if isinstance(v, SyntheticDataParams):
                    attributes[k] = v.json()
                elif isinstance(v, List):
                    attributes[k] = json.dumps(v)
                else:
                    attributes[k] = v

        return attributes

    def json(self):
        return json.dumps(self.dict())

    def prepare(self):
        if self.object_name and self.object_list:
            raise ValueError("Both object_name and object_list cannot be set")

        if not self.object_name and not self.object_list:
            raise ValueError(
                "One of object_name and object_list should be set"
            )

        return self.dict()
