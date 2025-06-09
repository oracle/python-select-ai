import json
import typing
from abc import ABC
from dataclasses import dataclass, fields
from typing import List, Mapping

__all__ = ["SelectAIDataClass"]


@dataclass
class SelectAIDataClass(ABC):
    """SelectAIDataClass is an abstract container for all data
    models defined in the select_ai Python module
    """

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    @classmethod
    def keys(cls):
        return set([field.name for field in fields(cls)])

    def dict(self, exclude_null=True):
        attributes = {}
        for k, v in self.__dict__.items():
            if v is not None or not exclude_null:
                attributes[k] = v
        return attributes

    def json(self, exclude_null=True):
        return json.dumps(self.dict(exclude_null=exclude_null))

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None:
                if field.type is typing.Optional[int]:
                    setattr(self, field.name, int(value))
                elif field.type is typing.Optional[str]:
                    setattr(self, field.name, str(value))
                elif field.type is typing.Optional[bool]:
                    setattr(self, field.name, bool(value))
                elif field.type is typing.Optional[float]:
                    setattr(self, field.name, float(value))
                elif field.type is typing.Optional[Mapping] and isinstance(
                    value, (str, bytes, bytearray)
                ):
                    setattr(self, field.name, json.loads(value))
                elif field.type is typing.Optional[
                    List[typing.Mapping]
                ] and isinstance(value, (str, bytes, bytearray)):
                    setattr(self, field.name, json.loads(value))
