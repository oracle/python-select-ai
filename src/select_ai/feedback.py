# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------
from select_ai._enums import StrEnum


class FeedbackType(StrEnum):

    POSITIVE = "positive"
    NEGATIVE = "negative"


class FeedbackOperation(StrEnum):

    ADD = "add"
    DELETE = "delete"
