# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from dataclasses import dataclass
from typing import List, Mapping, Optional

import pytest

from select_ai._abc import SelectAIDataClass, _bool

pytestmark = pytest.mark.unit


@dataclass
class ScalarData(SelectAIDataClass):
    count: Optional[int] = None
    name: Optional[str] = None
    enabled: Optional[bool] = None
    ratio: Optional[float] = None


@dataclass
class JsonData(SelectAIDataClass):
    payload: Optional[List[Mapping]] = None


def test_4000_bool_accepts_supported_values():
    assert _bool(True) is True
    assert _bool(0) is False
    assert _bool("yes") is True
    assert _bool("0") is False


def test_4001_bool_rejects_invalid_value():
    with pytest.raises(ValueError):
        _bool("maybe")


def test_4002_dict_excludes_null_values_by_default():
    data = ScalarData(count=1, name=None)
    assert data.dict() == {"count": 1}


def test_4003_dict_can_include_null_values():
    data = ScalarData(count=1, name=None)
    assert data.dict(exclude_null=False) == {
        "count": 1,
        "name": None,
        "enabled": None,
        "ratio": None,
    }


def test_4004_json_serializes_dictionary_payload():
    data = ScalarData(count=1, name="value")
    assert json.loads(data.json()) == {"count": 1, "name": "value"}


def test_4005_item_access_reads_and_writes_attributes():
    data = ScalarData(count=1)
    assert data["count"] == 1
    data["name"] = "updated"
    assert data.name == "updated"


def test_4006_post_init_coerces_scalar_types():
    data = ScalarData(count="7", name=10, enabled="true", ratio="2.5")
    assert data.count == 7
    assert data.name == "10"
    assert data.enabled is True
    assert data.ratio == 2.5


def test_4007_post_init_decodes_json_fields():
    data = JsonData(payload='[{"owner": "SH", "name": "EMP"}]')
    assert data.payload == [{"owner": "SH", "name": "EMP"}]
