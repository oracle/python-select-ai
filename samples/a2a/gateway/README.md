# Dynamic A2A gateway samples

These samples connect to a dynamic gateway, submit its A2UI database
connection form, open a temporary worker session, and execute Select AI tasks
against the database.

The gateway advertises `streaming: false` and supports request/response task
operations. Long-running work is returned as a task and can be followed with
`tasks/get`.

The gateway supports asynchronous work with `message/send` and
`configuration.blocking: false`, followed by `tasks/get`.

These samples use the A2A v0.3 JSON-RPC names used by the existing samples:
`message/send`, `tasks/get`, and `tasks/cancel`. A client using A2A 1.0 should
send `A2A-Version: 1.0` and use `SendMessage`, `GetTask`, `ListTasks`, and
`CancelTask`; its non-blocking option is `configuration.returnImmediately`.
The gateway accepts both versions, but streaming is disabled in both.

## Local setup

Install the A2A extra if necessary:

```bash
source .venv/bin/activate
pip install -e '.[a2a]'
```

Run these commands in three terminals from the repository root.

Terminal 1, Consul:

```bash
consul agent -dev -bind=127.0.0.1 -client=127.0.0.1
```

Terminal 2, one worker:

```bash
source .venv/bin/activate

CONSUL_HTTP_URL=http://127.0.0.1:8500 \
WORKER_ID=local-worker \
WORKER_ADDRESS=127.0.0.1 \
WORKER_PORT=8081 \
select-ai a2a worker --host 127.0.0.1 --port 8081
```

Terminal 3, the gateway:

```bash
source .venv/bin/activate

select-ai a2a gateway \
  --host 127.0.0.1 \
  --port 8000 \
  --agent-url http://127.0.0.1:8000 \
  --consul-url http://127.0.0.1:8500
```

The worker must be able to connect to the database when a sample submits the
form. Export the same values used by the other samples, plus the optional
team name:

```bash
export SELECT_AI_DB_CONNECT_STRING='<database DSN>'
export SELECT_AI_USER='<database user>'
export SELECT_AI_PASSWORD='<database password>'
export SELECT_AI_A2A_TEAM='ORACLE_AI_DATABASE_AGENT'
```

For a TNS-alias DSN, set `TNS_ADMIN` in the worker terminal before starting
the worker. Wallet-based Oracle Database mTLS is not currently supported by
the gateway session connection path.

## Run the samples

The gateway-specific samples perform the connection-form handshake
automatically and validate that the final artifact is
`database-agent-result`.

Blocking database task:

```bash
python samples/a2a/gateway/blocking_task.py
```

Non-blocking database task with polling:

```bash
python samples/a2a/gateway/task_poll.py
```

Expected task output is similar to:

```text
Task <uuid>: completed
Artifact: database-agent-result
...
```

For a quick health check:

```bash
curl http://127.0.0.1:8081/health
curl -sS http://127.0.0.1:8000/.well-known/agent-card.json | jq
```
