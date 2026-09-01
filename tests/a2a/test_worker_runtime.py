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

pytest.importorskip("fastapi")

import select_ai
from select_ai.agent.a2a import GatewaySettings, worker
from select_ai.agent.a2a.gateway import GatewayExecutor, _a2ui_part
from select_ai.agent.a2a.results import message_parts
from select_ai.agent.a2a.worker_client import WorkerClient


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


def test_worker_uses_pipe_process_and_returns_raw_result(monkeypatch):
    parent = FakeConnection(
        [{"type": "ready"}, {"type": "result", "result": "hi"}]
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
    result = asyncio.run(session_worker.send_prompt("session-1", "hello"))

    assert result == "hi"
    assert child.closed
    assert processes[0].target is worker._session_process_main
    assert processes[0].daemon is True
    assert parent.sent == [{"type": "run", "prompt": "hello"}]


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


def test_session_runtime_uses_one_async_connection_and_returns_raw_result(
    monkeypatch,
):
    connection = FakeConnection(
        [{"type": "run", "prompt": "hello"}, {"type": "close"}]
    )
    connection_arguments = {}

    class Conversation:
        def __init__(self, attributes):
            self.attributes = attributes

        async def create(self):
            return "conversation-1"

    class Team:
        def __init__(self, team_name):
            assert team_name == "TEAM"

        async def run(self, prompt, params):
            assert prompt == "hello"
            assert params == {"conversation_id": "conversation-1"}
            return (
                '{"metadata":{"mimeType":"application/json+a2ui"},'
                '"data":[]}'
            )

    async def async_connect(**kwargs):
        connection_arguments.update(kwargs)

    async def connected():
        return True

    async def disconnect():
        return None

    monkeypatch.setattr(select_ai, "async_connect", async_connect)
    monkeypatch.setattr(select_ai, "async_is_connected", connected)
    monkeypatch.setattr(select_ai, "async_disconnect", disconnect)
    monkeypatch.setattr(select_ai, "AsyncConversation", Conversation)
    monkeypatch.setattr(select_ai.agent, "AsyncTeam", Team)

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
        "result": (
            '{"metadata":{"mimeType":"application/json+a2ui"},' '"data":[]}'
        ),
    }


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


def test_worker_client_returns_the_raw_team_result(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def raise_for_status():
            return None

        text = "team result"

    monkeypatch.setattr(
        "select_ai.agent.a2a.worker_client.requests.post",
        lambda *args, **kwargs: Response(),
    )
    client = WorkerClient.__new__(WorkerClient)
    monkeypatch.setattr(
        client,
        "_route_for",
        lambda session_id: type("Route", (), {"endpoint": "http://worker"})(),
    )

    assert client.send_prompt("context-1", "hello") == "team result"


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

    part = _a2ui_part(
        {"version": "v0.9", "createSurface": {"surfaceId": "form"}}
    )

    assert MessageToDict(part.data) == {
        "version": "v0.9",
        "createSurface": {"surfaceId": "form"},
    }
    assert MessageToDict(part.metadata) == {
        "mimeType": "application/json+a2ui"
    }


def test_a2ui_action_reads_an_operation_list_or_single_operation():
    action = GatewayExecutor._a2ui_action(
        type(
            "Context",
            (),
            {
                "message": type(
                    "Message",
                    (),
                    {
                        "parts": [
                            _a2ui_part(
                                {
                                    "version": "v0.9",
                                    "action": {
                                        "name": "submit_database_connection"
                                    },
                                }
                            )
                        ]
                    },
                )()
            },
        )()
    )

    assert action == {"name": "submit_database_connection"}


def test_gateway_returns_connection_error_when_worker_rejects_opening():
    executor = GatewayExecutor.__new__(GatewayExecutor)
    executor.sessions = {}

    class Client:
        @staticmethod
        def open_session(_context_id, _session_info):
            raise requests.HTTPError("worker rejected the connection")

    executor.worker_client = Client()

    parts = asyncio.run(
        executor._open_session(
            {
                "dsn": "database",
                "username": "user",
                "password": "password",
                "team_name": "TEAM",
            },
            "context-1",
        )
    )

    assert parts[0].text.startswith("Could not connect.")
    assert executor.sessions == {}
