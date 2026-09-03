# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Typed values for the private Gateway-to-Worker session protocol."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from a2a.types.a2a_pb2 import ListTasksResponse, Message, Task
from a2a.utils.errors import TaskNotFoundError

WORKER_A2A_METHOD_HEADER = "x-select-ai-a2a-method"
WORKER_RESULT_KIND_HEADER = "x-select-ai-a2a-result-kind"
PROTOBUF_CONTENT_TYPE = "application/x-protobuf"


class PipeMessageType(str, Enum):
    """Message types exchanged over a session process pipe."""

    A2A = "a2a"
    CLOSE = "close"
    READY = "ready"
    RESULT = "result"
    ERROR = "error"
    A2A_ERROR = "a2a_error"


class A2AMethod(str, Enum):
    """A2A operations supported by the private session runtime."""

    SEND_MESSAGE = "SendMessage"
    GET_TASK = "GetTask"
    LIST_TASKS = "ListTasks"
    CANCEL_TASK = "CancelTask"
    DELETE_TASK = "DeleteTask"


class ResultKind(str, Enum):
    """Response types returned by a session runtime."""

    NONE = "none"
    TASK_NOT_FOUND = "task_not_found"
    TASK = "task"
    MESSAGE = "message"
    LIST_TASKS = "list_tasks"


@dataclass(frozen=True)
class WorkerResult:
    """One typed response from the worker session runtime."""

    kind: ResultKind
    payload: bytes = b""


def parse_request(message_type, payload: bytes):
    """Parse one protobuf request from the internal wire format."""
    message = message_type()
    message.ParseFromString(payload)
    return message


def encode_result(value) -> WorkerResult:
    """Encode one supported A2A response as protobuf wire bytes."""
    if value is None:
        return WorkerResult(ResultKind.NONE)
    if isinstance(value, Task):
        kind = ResultKind.TASK
    elif isinstance(value, Message):
        kind = ResultKind.MESSAGE
    elif isinstance(value, ListTasksResponse):
        kind = ResultKind.LIST_TASKS
    else:
        raise TypeError(f"Unsupported A2A response type: {type(value)!r}")
    return WorkerResult(kind, value.SerializeToString())


def decode_result(result: WorkerResult, expected_type=None):
    """Decode a session runtime response from protobuf wire bytes."""
    kind = result.kind
    if kind == ResultKind.TASK_NOT_FOUND:
        raise TaskNotFoundError
    if kind == ResultKind.NONE:
        return None
    payload = result.payload
    if not payload:
        return None
    message_type = expected_type or {
        ResultKind.TASK: Task,
        ResultKind.MESSAGE: Message,
        ResultKind.LIST_TASKS: ListTasksResponse,
    }.get(kind)
    if message_type is None:
        raise ValueError(f"Unsupported A2A result kind: {kind}")
    message = message_type()
    message.ParseFromString(payload)
    return message
