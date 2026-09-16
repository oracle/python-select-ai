# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

"""Embedded session routing for dynamic standalone A2A deployment."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from contextlib import asynccontextmanager
from threading import Event, Lock, Thread
from uuid import uuid4

from a2a.types.a2a_pb2 import (
    CancelTaskRequest,
    GetTaskRequest,
    ListTasksRequest,
    ListTasksResponse,
    Message,
    SendMessageRequest,
    Task,
)

from select_ai.agent.a2a.forms import validate_connection_form
from select_ai.agent.a2a.gateway import create_session_app
from select_ai.agent.a2a.models import (
    SessionInfo,
    StandaloneSessionSettings,
)
from select_ai.agent.a2a.session_process import (
    ProcessSessionBackend,
    SessionNotFound,
    SessionSpec,
    SessionUnavailable,
)
from select_ai.agent.a2a.worker_client import ReconnectRequired
from select_ai.agent.a2a.worker_protocol import (
    A2AMethod,
    decode_result,
)


class EmbeddedSessionClient:
    """Expose the clustered client contract over an in-process router."""

    def __init__(self, settings: StandaloneSessionSettings) -> None:
        self.backend = ProcessSessionBackend(
            settings.session_ttl_seconds,
            settings.session_start_timeout_seconds,
        )
        self._bindings: dict[tuple[str, str], str] = {}
        self._tasks: dict[tuple[str, str], str] = {}
        self._routing_lock = Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: Thread | None = None
        self._reaper: Future | None = None

    def start(self) -> None:
        """Start the private event loop that owns the async backend."""
        if self._loop is not None:
            return
        ready = Event()

        def run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()
            loop.close()

        self._thread = Thread(
            target=run_loop,
            name="select-ai-a2a-sessions",
            daemon=True,
        )
        self._thread.start()
        ready.wait()
        self._reaper = asyncio.run_coroutine_threadsafe(
            self.backend.reap_expired(),
            self._require_loop(),
        )

    def shutdown(self) -> None:
        """Close every child process and stop the private event loop."""
        if self._loop is None:
            return
        if self._reaper is not None:
            self._reaper.cancel()
        self._run(self.backend.close_all())
        loop = self._require_loop()
        loop.call_soon_threadsafe(loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=10)
        self._loop = None
        self._thread = None
        self._reaper = None
        with self._routing_lock:
            self._bindings.clear()
            self._tasks.clear()

    def open_session(
        self,
        owner: str,
        context_id: str,
        session_info: SessionInfo,
    ) -> str:
        """Create one isolated child and atomically bind it to a context."""
        session_id = str(uuid4())
        self._run(
            self.backend.open(
                SessionSpec(
                    session_id=session_id,
                    owner=owner,
                    dsn=session_info.dsn,
                    username=session_info.username,
                    password=session_info.password,
                    team_name=session_info.team_name,
                )
            )
        )
        key = (owner, context_id)
        with self._routing_lock:
            created = key not in self._bindings
            if created:
                self._bindings[key] = session_id
        if not created:
            self._run(self.backend.close(session_id))
            raise RuntimeError("A database session already exists.")
        return session_id

    def session_exists(self, owner: str, context_id: str) -> bool:
        """Return whether the owner/context binding still has a live child."""
        session_id = self._session_id(owner, context_id)
        if session_id is None:
            return False
        try:
            self._run(self.backend.get(session_id))
        except SessionNotFound:
            self._drop_binding(owner, context_id, session_id)
            return False
        return True

    def send_message(
        self,
        owner: str,
        context_id: str,
        request: SendMessageRequest,
    ) -> Task | Message | None:
        result = self._dispatch(
            owner,
            context_id,
            A2AMethod.SEND_MESSAGE,
            request,
        )
        value = decode_result(result)
        if isinstance(value, Task):
            with self._routing_lock:
                self._tasks[(owner, value.id)] = context_id
        return value

    def get_task(self, owner: str, request: GetTaskRequest) -> Task | None:
        context_id = self._task_context(owner, request.id)
        if context_id is None:
            return None
        value = decode_result(
            self._dispatch(owner, context_id, A2AMethod.GET_TASK, request)
        )
        return value if isinstance(value, Task) else None

    def list_tasks(
        self,
        owner: str,
        context_id: str,
        request: ListTasksRequest,
    ) -> ListTasksResponse:
        return (
            decode_result(
                self._dispatch(
                    owner, context_id, A2AMethod.LIST_TASKS, request
                )
            )
            or ListTasksResponse()
        )

    def cancel_task(self, owner: str, task_id: str) -> Task | None:
        context_id = self._task_context(owner, task_id)
        if context_id is None:
            return None
        value = decode_result(
            self._dispatch(
                owner,
                context_id,
                A2AMethod.CANCEL_TASK,
                CancelTaskRequest(id=task_id),
            )
        )
        return value if isinstance(value, Task) else None

    def close_session(self, owner: str, context_id: str) -> None:
        """Close and forget one owner/context binding."""
        with self._routing_lock:
            session_id = self._bindings.pop((owner, context_id), None)
        if session_id is None:
            return
        try:
            self._run(self.backend.close(session_id))
        except SessionNotFound:
            pass

    def _dispatch(self, owner, context_id, method, request):
        session_id = self._session_id(owner, context_id)
        if session_id is None:
            raise ReconnectRequired(
                "Database session expired; reconnect required.",
                context_id,
            )
        try:
            return self._run(
                self.backend.dispatch(
                    session_id,
                    method.value,
                    request.SerializeToString(),
                )
            )
        except (SessionNotFound, SessionUnavailable) as error:
            self._drop_binding(owner, context_id, session_id)
            raise ReconnectRequired(str(error), context_id) from error

    def _session_id(self, owner: str, context_id: str) -> str | None:
        with self._routing_lock:
            return self._bindings.get((owner, context_id))

    def _task_context(self, owner: str, task_id: str) -> str | None:
        with self._routing_lock:
            return self._tasks.get((owner, task_id))

    def _drop_binding(
        self,
        owner: str,
        context_id: str,
        session_id: str,
    ) -> None:
        with self._routing_lock:
            key = (owner, context_id)
            if self._bindings.get(key) == session_id:
                self._bindings.pop(key, None)

    def _run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(
            coroutine,
            self._require_loop(),
        ).result()

    def _require_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("Embedded session manager is not running.")
        return self._loop


def create_embedded_session_app(
    settings: StandaloneSessionSettings,
):
    """Build a dynamic standalone app backed by local child processes."""
    form_template = settings.connection_form_template
    if form_template is not None:
        form_template = validate_connection_form(
            list(form_template),
            settings.connection.missing_fields,
        )
    client = EmbeddedSessionClient(settings)

    @asynccontextmanager
    async def lifespan(_app):
        client.start()
        try:
            yield
        finally:
            await asyncio.to_thread(client.shutdown)

    return create_session_app(
        public_url=settings.public_url,
        session_client=client,
        connection=settings.connection,
        connection_form_template=form_template,
        require_oauth=settings.require_oauth,
        description=settings.description,
        lifespan=lifespan,
    )
