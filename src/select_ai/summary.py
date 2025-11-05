# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from typing import Optional

from select_ai._abc import SelectAIDataClass
from select_ai._enums import StrEnum


class Style(StrEnum):

    PARAGRAPH = "paragraph"
    LIST = "list"


class ChunkProcessingMethod(StrEnum):

    ITERATIVE_REFINEMENT = "iterative_refinement"
    MAP_REDUCE = "map_reduce"


class ExtractivenessLevel(StrEnum):

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SummaryParams(SelectAIDataClass):
    """
    Customize summary generation using these parameters

    :param int min_words: approximate minimum number of words the generated
     summary is expected to contain.

    :param int max_words: approximate maximum number of words the generated
     summary is expected to contain.

    :param select_ai.summary.Style summary_style: Specifies the format
     style for the summary

    :param select_ai.summary.ChunkProcessingMethod chunk_processing_method:
     When the text exceeds the token limit that the LLM can process, it must
     be split into manageable chunks

    :param select_ai.summary.ExtractivenessLevel extractiveness_level:
     Determines how closely the summary follows the original wording
     of the input
    """

    min_words: Optional[int] = None
    max_words: Optional[int] = None
    summary_style: Optional[Style] = None
    chunk_processing_method: Optional[ChunkProcessingMethod] = None
    extractiveness_level: Optional[ExtractivenessLevel] = None
