# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Unit tests for the private multiprocessing session runtime."""

import asyncio

import pytest
import requests
from google.protobuf.json_format import MessageToJson

pytest.importorskip("fastapi")

import select_ai
from a2a.helpers import new_data_part, new_text_part
from a2a.server.context import ServerCallContext
from a2a.types.a2a_pb2 import (
    CancelTaskRequest,
    GetTaskRequest,
    ListTasksRequest,
    Message,
    Role,
    SendMessageRequest,
    Task,
    TaskState,
)
from a2a.utils.errors import (
    InvalidParamsError,
    TaskNotFoundError,
    UnsupportedOperationError,
)
from select_ai.agent.a2a import GatewaySettings, session_runtime, worker
from select_ai.agent.a2a.a2ui import (
    A2UI_CATALOG_ID,
    A2UI_EXTENSION_URI,
    A2UI_VERSION,
    a2ui_part,
    find_action,
)
from select_ai.agent.a2a.forms import connection_form
from select_ai.agent.a2a.gateway import GatewayRequestHandler
from select_ai.agent.a2a.results import message_parts
from select_ai.agent.a2a.worker_client import ReconnectRequired, WorkerClient
from select_ai.agent.a2a.worker_protocol import (
    A2AMethod,
    ResultKind,
    WorkerResult,
    decode_result,
)


class FakeConnection:
    """Small synchronous pipe stand-in for worker protocol tests."""

    def __init__(self, responses=()):
        self.responses = list(responses)
        self.sent = []
        self.closed = False

    def send(self, value):
        self.sent.append(value)

    def poll(self, _timeout):
        return bool(self.responses)

    def recv(self):
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class FakeProcess:
    """Process stand-in which lets tests assert IPC without forking."""

    def __init__(self, *, target, args, daemon):
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        self.alive = True

    def start(self):
        self.started = True

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        del timeout

    def terminate(self):
        self.alive = False

    def kill(self):
        self.alive = False


def test_worker_uses_pipe_process_and_dispatches_a2a(monkeypatch):
    parent = FakeConnection(
        [
            {"type": "ready"},
            {
                "type": "result",
                "result": WorkerResult(ResultKind.NONE),
            },
        ]
    )
    child = FakeConnection()
    processes = []

    def process_factory(**kwargs):
        process = FakeProcess(**kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(
        worker.multiprocessing,
        "Pipe",
        lambda: (parent, child),
    )
    monkeypatch.setattr(worker.multiprocessing, "Process", process_factory)
    session_worker = worker.SessionWorker(60, 1)
    request = worker.OpenSessionRequest(
        session_id="session-1",
        username="user",
        password="password",
        dsn="database",
        team_name="TEAM",
    )

    asyncio.run(session_worker.open(request))
    task_request = GetTaskRequest(id="task-1")
    result = asyncio.run(
        session_worker.dispatch(
            "session-1",
            "GetTask",
            task_request.SerializeToString(),
        )
    )

    assert result == WorkerResult(ResultKind.NONE)
    assert child.closed
    assert processes[0].target is worker._session_process_main
    assert processes[0].daemon is True
    assert parent.sent == [
        {
            "type": "a2a",
            "method": "GetTask",
            "payload": task_request.SerializeToString(),
        }
    ]


def test_expired_session_closes_the_process_and_pipe(monkeypatch):
    parent = FakeConnection([{"type": "ready"}])
    child = FakeConnection()
    process = None

    def process_factory(**kwargs):
        nonlocal process
        process = FakeProcess(**kwargs)
        return process

    monkeypatch.setattr(
        worker.multiprocessing,
        "Pipe",
        lambda: (parent, child),
    )
    monkeypatch.setattr(worker.multiprocessing, "Process", process_factory)
    session_worker = worker.SessionWorker(60, 1)
    request = worker.OpenSessionRequest(
        session_id="session-1",
        username="user",
        password="password",
        dsn="database",
        team_name="TEAM",
    )
    asyncio.run(session_worker.open(request))
    session_worker.sessions["session-1"].expires_at = 0

    with pytest.raises(worker.HTTPException, match="reconnect required"):
        asyncio.run(session_worker.get("session-1"))

    assert process is not None
    assert process.alive is False
    assert parent.closed
    assert parent.sent == [{"type": "close"}]


def test_session_reaper_closes_idle_expired_process(monkeypatch):
    parent = FakeConnection([{"type": "ready"}])
    child = FakeConnection()
    process = None

    def process_factory(**kwargs):
        nonlocal process
        process = FakeProcess(**kwargs)
        return process

    monkeypatch.setattr(
        worker.multiprocessing,
        "Pipe",
        lambda: (parent, child),
    )
    monkeypatch.setattr(worker.multiprocessing, "Process", process_factory)
    monkeypatch.setattr(worker, "_SESSION_REAPER_INTERVAL_SECONDS", 0.01)
    session_worker = worker.SessionWorker(60, 1)
    request = worker.OpenSessionRequest(
        session_id="session-1",
        username="user",
        password="password",
        dsn="database",
        team_name="TEAM",
    )

    async def exercise_reaper():
        await session_worker.open(request)
        session_worker.sessions["session-1"].expires_at = 0
        reaper = asyncio.create_task(session_worker.reap_expired())
        try:
            await asyncio.wait_for(_wait_for_process_exit(process), 1)
        finally:
            reaper.cancel()
            with pytest.raises(asyncio.CancelledError):
                await reaper

    async def _wait_for_process_exit(session_process):
        while session_process is None or session_process.alive:
            await asyncio.sleep(0.01)

    asyncio.run(exercise_reaper())

    assert process is not None
    assert parent.closed
    assert parent.sent == [{"type": "close"}]
    assert session_worker.sessions == {}


def test_session_runtime_uses_one_async_connection_and_dispatches_a2a(
    monkeypatch,
):
    connection = FakeConnection(
        [
            {
                "type": "a2a",
                "method": "GetTask",
                "payload": GetTaskRequest(id="t1").SerializeToString(),
            },
            {"type": "close"},
        ]
    )
    connection_arguments = {}

    class Runtime:
        def __init__(self, session_id, team_name):
            assert session_id == "session-1"
            assert team_name == "TEAM"

        async def initialize(self):
            return None

        async def handle(self, method, payload):
            assert method == "GetTask"
            assert GetTaskRequest.FromString(payload).id == "t1"
            return WorkerResult(ResultKind.NONE)

    async def async_connect(**kwargs):
        connection_arguments.update(kwargs)

    async def connected():
        return True

    async def disconnect():
        return None

    monkeypatch.setattr(select_ai, "async_connect", async_connect)
    monkeypatch.setattr(select_ai, "async_is_connected", connected)
    monkeypatch.setattr(select_ai, "async_disconnect", disconnect)
    monkeypatch.setattr(worker, "SessionRuntime", Runtime)

    asyncio.run(
        worker._run_session_process(
            connection,
            {
                "user": "user",
                "password": "password",
                "dsn": "database",
            },
            "session-1",
            "TEAM",
        )
    )

    assert connection_arguments == {
        "user": "user",
        "password": "password",
        "dsn": "database",
    }
    assert connection.sent[0] == {"type": "ready"}
    assert connection.sent[1] == {
        "type": "result",
        "result": WorkerResult(ResultKind.NONE),
    }


def test_session_runtime_builds_oracle_backed_default_handler(monkeypatch):
    initialized = []

    class Team:
        @staticmethod
        async def fetch(team_name):
            assert team_name == "TEAM"
            initialized.append("team")

    class Store:
        async def initialize(self):
            initialized.append(self)

    class Handler:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(session_runtime, "OracleTaskStore", Store)
    monkeypatch.setattr(session_runtime, "OracleContextStore", Store)
    monkeypatch.setattr(session_runtime, "AsyncTeam", Team)
    monkeypatch.setattr(session_runtime, "DefaultRequestHandler", Handler)
    monkeypatch.setattr(
        session_runtime,
        "DatabaseTeamExecutor",
        lambda team_name, context_store: (team_name, context_store),
    )
    monkeypatch.setattr(
        session_runtime,
        "_build_agent_card",
        lambda *args: "agent-card",
    )

    runtime = session_runtime.SessionRuntime("session-1", "TEAM")
    asyncio.run(runtime.initialize())

    assert initialized == [
        "team",
        runtime.task_store,
        runtime.context_store,
    ]
    assert runtime.handler.kwargs["task_store"] is runtime.task_store
    assert runtime.handler.kwargs["agent_card"] == "agent-card"


def test_session_runtime_rejects_unknown_team_before_initializing_stores(
    monkeypatch,
):
    initialized = []

    class Team:
        @staticmethod
        async def fetch(team_name):
            assert team_name == "MISSPELLED_TEAM"
            raise RuntimeError("team does not exist")

    class Store:
        async def initialize(self):
            initialized.append(self)

    monkeypatch.setattr(session_runtime, "AsyncTeam", Team)
    monkeypatch.setattr(session_runtime, "OracleTaskStore", Store)
    monkeypatch.setattr(session_runtime, "OracleContextStore", Store)

    runtime = session_runtime.SessionRuntime("session-1", "MISSPELLED_TEAM")
    with pytest.raises(RuntimeError, match="team does not exist"):
        asyncio.run(runtime.initialize())

    assert initialized == []
    assert runtime.handler is None


def test_session_runtime_preserves_database_task_not_found():
    class Handler:
        async def on_get_task(self, _request, _context):
            raise TaskNotFoundError

    runtime = session_runtime.SessionRuntime("session-1", "TEAM")
    runtime.handler = Handler()

    result = asyncio.run(
        runtime.handle(
            A2AMethod.GET_TASK,
            GetTaskRequest(id="missing-task").SerializeToString(),
        )
    )

    assert result == WorkerResult(ResultKind.TASK_NOT_FOUND)


def test_decode_result_raises_only_for_explicit_database_task_not_found():
    with pytest.raises(TaskNotFoundError):
        decode_result(WorkerResult(ResultKind.TASK_NOT_FOUND))

    assert decode_result(WorkerResult(ResultKind.NONE)) is None


def test_gateway_rejects_unsupported_stream():
    async def consume_stream():
        stream = GatewayRequestHandler.on_message_send_stream(None, None)
        with pytest.raises(UnsupportedOperationError):
            await anext(stream)

    asyncio.run(consume_stream())


def test_message_parts_preserves_serialized_text_and_data_parts():
    parts = message_parts(
        """{
            "kind": "message",
            "parts": [
                {"kind": "text", "text": "hello"},
                {
                    "kind": "data",
                    "data": {"value": 1},
                    "metadata": {"mimeType": "application/json+a2ui"}
                }
            ]
        }"""
    )

    assert parts is not None
    assert parts[0].text == "hello"
    assert parts[1].WhichOneof("content") == "data"


def test_worker_client_forwards_and_parses_a2a_message(monkeypatch):
    sent = {}

    class Response:
        status_code = 200
        headers = {"x-select-ai-a2a-result-kind": "message"}
        content = Message(
            message_id="m1",
            role=Role.ROLE_AGENT,
            parts=[new_text_part("hello")],
        ).SerializeToString()

        @staticmethod
        def raise_for_status():
            return None

    def post(*args, **kwargs):
        del args
        sent.update(kwargs)
        return Response()

    monkeypatch.setattr(
        "select_ai.agent.a2a.worker_client.requests.post",
        post,
    )
    client = WorkerClient.__new__(WorkerClient)
    monkeypatch.setattr(
        client,
        "_route_for",
        lambda session_id: type("Route", (), {"endpoint": "http://worker"})(),
    )

    request = SendMessageRequest(
        message=Message(
            message_id="m1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )
    result = client.send_message("context-1", request)

    assert result is not None
    assert result.message_id == "m1"
    assert result.parts[0].text == "hello"
    assert sent["headers"] == {
        "content-type": "application/x-protobuf",
        "x-select-ai-a2a-method": "SendMessage",
    }
    assert sent["data"] == request.SerializeToString()


def test_worker_client_uses_consul_https_endpoint_with_mtls(monkeypatch):
    settings = GatewaySettings(
        agent_url="https://gateway.example.com",
        consul_url="http://consul:8500",
        worker_service="select-ai-worker",
        session_ttl_seconds=60,
        worker_tls_ca_file="/tls/ca.pem",
        worker_tls_cert_file="/tls/gateway.pem",
        worker_tls_key_file="/tls/gateway-key.pem",
    )
    client = WorkerClient(settings)

    class Response:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return [
                {
                    "Service": {
                        "Meta": {"endpoint": "https://worker-0.internal"}
                    },
                    "Node": {},
                }
            ]

    monkeypatch.setattr(
        "select_ai.agent.a2a.worker_client.requests.get",
        lambda *args, **kwargs: Response(),
    )

    assert client._select_worker() == "https://worker-0.internal"
    assert client._worker_request_kwargs == {
        "verify": "/tls/ca.pem",
        "cert": ("/tls/gateway.pem", "/tls/gateway-key.pem"),
    }


def test_mtls_requires_all_three_gateway_files():
    with pytest.raises(ValueError, match="worker mTLS requires"):
        GatewaySettings(
            agent_url="https://gateway.example.com",
            consul_url="http://consul:8500",
            worker_service="select-ai-worker",
            session_ttl_seconds=60,
            worker_tls_ca_file="/tls/ca.pem",
        )


def test_worker_registers_its_https_endpoint(monkeypatch):
    registered = {}

    class Response:
        @staticmethod
        def raise_for_status():
            return None

    class Client:
        def __init__(self, **kwargs):
            del kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def put(self, _url, json):
            registered.update(json)
            return Response()

    monkeypatch.setattr(worker.httpx, "AsyncClient", Client)
    asyncio.run(
        worker._register_with_consul(
            "http://consul:8500",
            "worker-0",
            "10.0.0.1",
            8080,
            "https://worker-0.internal",
        )
    )

    assert registered["Meta"] == {"endpoint": "https://worker-0.internal"}


def test_a2ui_operation_uses_a_metadata_marked_data_part():
    from google.protobuf.json_format import MessageToDict

    part = a2ui_part(
        {"version": "v0.9", "createSurface": {"surfaceId": "form"}}
    )

    assert MessageToDict(part.data) == {
        "version": "v0.9",
        "createSurface": {"surfaceId": "form"},
    }
    assert MessageToDict(part.metadata) == {
        "mimeType": "application/json+a2ui"
    }


def test_each_connection_form_uses_one_new_unique_surface():
    first = connection_form()
    second = connection_form()

    first_surface_ids = [
        operation[message_type]["surfaceId"]
        for operation, message_type in zip(
            first,
            ("createSurface", "updateComponents", "updateDataModel"),
        )
    ]
    second_surface_id = second[0]["createSurface"]["surfaceId"]

    assert len(set(first_surface_ids)) == 1
    assert first_surface_ids[0].startswith("db-connect-")
    assert first_surface_ids[0] != second_surface_id


def test_connection_form_matches_advertised_a2ui_version():
    assert A2UI_EXTENSION_URI.endswith(f"/{A2UI_VERSION}")
    assert f"/{A2UI_VERSION.replace('.', '_')}/" in A2UI_CATALOG_ID
    assert all(
        operation["version"] == A2UI_VERSION for operation in connection_form()
    )


def test_connection_action_reads_an_operation_list_or_single_operation():
    action = find_action(
        Message(
            role=Role.ROLE_USER,
            parts=[
                a2ui_part(
                    {
                        "version": "v0.9",
                        "action": {"name": "submit_database_connection"},
                    }
                )
            ],
        ),
        "submit_database_connection",
    )

    assert action == {"name": "submit_database_connection"}


def test_connection_action_accepts_gemini_unmarked_data_part():
    action = find_action(
        Message(
            role=Role.ROLE_USER,
            parts=[
                new_data_part(
                    {
                        "version": "v0.9",
                        "action": {
                            "name": "submit_database_connection",
                            "context": {"team_name": "TEAM"},
                        },
                    }
                )
            ],
        ),
        "submit_database_connection",
    )

    assert action == {
        "name": "submit_database_connection",
        "context": {"team_name": "TEAM"},
    }


def test_gateway_returns_connection_error_when_worker_rejects_opening():
    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)

    class Client:
        @staticmethod
        def open_session(_context_id, _session_info):
            raise requests.HTTPError("worker rejected the connection")

    handler.worker_client = Client()

    session_id = asyncio.run(
        handler._open_session(
            {
                "dsn": "database",
                "username": "user",
                "password": "password",
                "team_name": "TEAM",
            },
            "context-1",
        )
    )

    assert session_id is None


def test_gateway_bootstrap_is_transient_until_worker_session_opens():
    class Client:
        def __init__(self):
            self.opened = False
            self.saved = None

        def session_exists(self, _session_id):
            return self.opened

        def open_session(self, session_id, session_info):
            assert session_id == "context-1"
            assert session_info.team_name == "TEAM"
            self.opened = True
            return session_id

    client = Client()
    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = client

    form_request = SendMessageRequest(
        message=Message(
            message_id="m1",
            context_id="context-1",
            role=Role.ROLE_USER,
            parts=[new_text_part("connect")],
        )
    )
    form_task = asyncio.run(
        handler.on_message_send(form_request, ServerCallContext())
    )

    assert isinstance(form_task, Task)
    assert form_task.context_id == "context-1"
    assert form_task.artifacts[0].name == "database-connection-form"
    assert len(form_task.artifacts[0].parts) == 3

    connect_request = SendMessageRequest(
        message=Message(
            message_id="m2",
            task_id=form_task.id,
            context_id=form_task.context_id,
            role=Role.ROLE_USER,
            parts=[
                a2ui_part(
                    {
                        "version": "v0.9",
                        "action": {
                            "name": "submit_database_connection",
                            "context": {
                                "dsn": "database",
                                "username": "user",
                                "password": "password",
                                "team_name": "TEAM",
                            },
                        },
                    }
                )
            ],
        )
    )
    connected_task = asyncio.run(
        handler.on_message_send(connect_request, ServerCallContext())
    )

    assert connected_task.status.state == TaskState.TASK_STATE_COMPLETED
    assert all(item.message_id != "m2" for item in connected_task.history)
    assert '"password": "password"' not in MessageToJson(connected_task)


def test_gateway_replaces_bootstrap_task_with_worker_owned_task():
    class Client:
        calls = 0

        @staticmethod
        def session_exists(_session_id):
            return True

        def send_message(self, session_id, request):
            assert session_id == "context-1"
            self.calls += 1
            if self.calls == 1:
                assert request.message.task_id == (
                    "gateway-bootstrap-form-task"
                )
                raise TaskNotFoundError
            assert not request.message.task_id
            return Task(
                id="worker-task",
                context_id=session_id,
                status={"state": TaskState.TASK_STATE_COMPLETED},
            )

    client = Client()
    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = client
    request = SendMessageRequest(
        message=Message(
            message_id="m3",
            task_id="gateway-bootstrap-form-task",
            context_id="context-1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    task = asyncio.run(handler.on_message_send(request, ServerCallContext()))

    assert task.id == "worker-task"
    assert task.context_id == "context-1"
    assert client.calls == 2


def test_gateway_preserves_missing_worker_task_error():
    class Client:
        @staticmethod
        def session_exists(_session_id):
            return True

        @staticmethod
        def send_message(_session_id, _request):
            raise TaskNotFoundError

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()
    request = SendMessageRequest(
        message=Message(
            message_id="m3",
            task_id="oracle-task-that-no-longer-exists",
            context_id="context-1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    with pytest.raises(TaskNotFoundError):
        asyncio.run(handler.on_message_send(request, ServerCallContext()))


def test_gateway_bootstrap_without_context_returns_transient_form_task():
    class Client:
        @staticmethod
        def session_exists(session_id):
            assert session_id
            return False

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()
    request = SendMessageRequest(
        message=Message(
            message_id="m1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    form_task = asyncio.run(
        handler.on_message_send(request, ServerCallContext())
    )

    assert isinstance(form_task, Task)
    assert form_task.id.startswith("gateway-bootstrap-")
    assert form_task.context_id
    # The connection form is a response-only gateway task. Its ID must not be
    # attached to the user's message because no corresponding task exists in
    # the worker's Oracle task store.
    assert not form_task.history[0].task_id
    assert form_task.status.state == TaskState.TASK_STATE_COMPLETED
    assert form_task.artifacts[0].name == "database-connection-form"
    assert len(form_task.artifacts[0].parts) == 3


def test_gateway_returns_task_form_when_task_session_expires_before_send():
    class Client:
        @staticmethod
        def get_task(_request):
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                "context-1",
            )

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()
    request = SendMessageRequest(
        message=Message(
            message_id="m1",
            task_id="task-1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    task = asyncio.run(handler.on_message_send(request, ServerCallContext()))

    assert isinstance(task, Task)
    assert task.id == "task-1"
    assert task.context_id == "context-1"
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_returns_task_form_when_task_route_is_missing_before_send():
    class Client:
        @staticmethod
        def get_task(_request):
            return None

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()
    request = SendMessageRequest(
        message=Message(
            message_id="m1",
            task_id="task-from-old-deployment",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    task = asyncio.run(handler.on_message_send(request, ServerCallContext()))

    assert isinstance(task, Task)
    assert task.id == "task-from-old-deployment"
    assert task.context_id
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_uses_task_form_for_expired_context_only_message():
    class Client:
        @staticmethod
        def session_exists(_session_id):
            return True

        @staticmethod
        def send_message(_session_id, _request):
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                "context-1",
            )

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()
    request = SendMessageRequest(
        message=Message(
            message_id="m1",
            context_id="context-1",
            role=Role.ROLE_USER,
            parts=[new_text_part("hello")],
        )
    )

    task = asyncio.run(handler.on_message_send(request, ServerCallContext()))

    assert isinstance(task, Task)
    assert task.id
    assert task.context_id == "context-1"
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_uses_connection_form_when_get_task_session_expires():
    class Client:
        @staticmethod
        def get_task(_request):
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                "context-1",
            )

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()

    task = asyncio.run(
        handler.on_get_task(
            GetTaskRequest(id="task-1"),
            ServerCallContext(),
        )
    )

    assert task.id == "task-1"
    assert task.context_id == "context-1"
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_uses_connection_form_when_get_task_route_is_missing():
    class Client:
        @staticmethod
        def get_task(_request):
            return None

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()

    task = asyncio.run(
        handler.on_get_task(
            GetTaskRequest(id="task-from-old-deployment"),
            ServerCallContext(),
        )
    )

    assert task.id == "task-from-old-deployment"
    assert task.context_id
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_uses_connection_form_when_cancel_task_session_expires():
    class Client:
        @staticmethod
        def cancel_task(_task_id):
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                "context-1",
            )

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()

    task = asyncio.run(
        handler.on_cancel_task(
            CancelTaskRequest(id="task-1"),
            ServerCallContext(),
        )
    )

    assert task.id == "task-1"
    assert task.context_id == "context-1"
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_uses_connection_form_when_cancel_task_route_is_missing():
    class Client:
        @staticmethod
        def cancel_task(_task_id):
            return None

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()

    task = asyncio.run(
        handler.on_cancel_task(
            CancelTaskRequest(id="task-from-old-deployment"),
            ServerCallContext(),
        )
    )

    assert task.id == "task-from-old-deployment"
    assert task.context_id
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert task.artifacts[0].name == "database-connection-form"
    assert len(task.artifacts[0].parts) == 3


def test_gateway_exposes_connection_form_data_when_list_session_expires():
    class Client:
        @staticmethod
        def list_tasks(_context_id, _request):
            raise ReconnectRequired(
                "Database session ended; reconnect required.",
                "context-1",
            )

    handler = GatewayRequestHandler.__new__(GatewayRequestHandler)
    handler.worker_client = Client()

    with pytest.raises(InvalidParamsError) as raised:
        asyncio.run(
            handler.on_list_tasks(
                ListTasksRequest(context_id="context-1"),
                ServerCallContext(),
            )
        )

    assert raised.value.data["reason"] == "SESSION_EXPIRED"
    assert raised.value.data["contextId"] == "context-1"
    assert raised.value.data["connectionForm"]
