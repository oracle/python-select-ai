# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import json
from dataclasses import dataclass
from typing import List, Mapping, Optional

from select_ai._abc import SelectAIDataClass


@dataclass
class SyntheticDataParams(SelectAIDataClass):
    """Optional parameters to control generation of synthetic data

    :param int sample_rows: number of rows from the table to use as a sample
     to guide the LLM in data generation

    :param bool table_statistics: Enable or disable the use of table
     statistics information. Default value is False

    :param str priority: Assign a priority value that defines the number of
     parallel requests sent to the LLM for generating synthetic data.
     Tasks with a higher priority will consume more database resources and
     complete faster. Possible values are: HIGH, MEDIUM, LOW

    :param bool comments: Enable or disable sending comments to the LLM to
     guide data generation. Default value is False

    """

    sample_rows: Optional[int] = None
    table_statistics: Optional[bool] = False
    priority: Optional[str] = "HIGH"
    comments: Optional[bool] = False


@dataclass
class SyntheticDataAttributes(SelectAIDataClass):
    """Attributes to control generation of synthetic data

    :param str object_name: Table name to populate synthetic data
    :param List[Mapping] object_list: Use this to generate synthetic data
     on multiple tables
    :param str owner_name: Database user who owns the referenced object.
     Default value is connected user's schema
    :param int record_count: Number of records to generate
    :param str user_prompt: User prompt to guide generation of synthetic data
     For e.g. "the release date for the movies should be in 2019"

    """

    object_name: Optional[str] = None
    object_list: Optional[List[Mapping]] = None
    owner_name: Optional[str] = None
    params: Optional[SyntheticDataParams] = None
    record_count: Optional[int] = None
    user_prompt: Optional[str] = None

    def __post_init__(self):
        if self.params and not isinstance(self.params, SyntheticDataParams):
            raise TypeError(
                "'params' must be an object of" " type SyntheticDataParams'"
            )

    def dict(self, exclude_null=True):
        attributes = {}
        for k, v in self.__dict__.items():
            if v is not None or not exclude_null:
                if isinstance(v, SyntheticDataParams):
                    attributes[k] = v.json(exclude_null=exclude_null)
                elif isinstance(v, List):
                    attributes[k] = json.dumps(v)
                else:
                    attributes[k] = v
        return attributes

    def prepare(self):
        if self.object_name and self.object_list:
            raise ValueError("Both object_name and object_list cannot be set")

        if not self.object_name and not self.object_list:
            raise ValueError(
                "One of object_name and object_list should be set"
            )

        return self.dict()
