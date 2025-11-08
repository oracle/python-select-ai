# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
import typing
from abc import ABC
from dataclasses import dataclass, fields
from typing import Any, List, Mapping

__all__ = ["SelectAIDataClass"]


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}")


def _is_json(field, value) -> bool:
    if field.type in (
        typing.List[Mapping],
        typing.Optional[Mapping],
        typing.Optional[List[str]],
        typing.Optional[List[typing.Mapping]],
    ) and isinstance(value, (str, bytes, bytearray)):
        return True
    return False


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
                    setattr(self, field.name, _bool(value))
                elif field.type is typing.Optional[float]:
                    setattr(self, field.name, float(value))
                elif _is_json(field, value):
                    setattr(self, field.name, json.loads(value))
                else:
                    setattr(self, field.name, value)
