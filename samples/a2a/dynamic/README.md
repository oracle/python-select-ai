# Dynamic A2A session samples

These samples connect to either standalone or clustered dynamic deployment,
inspect and submit its A2UI database connection form, and execute Select AI
tasks against the database.

The dynamic server advertises `streaming: false` and supports request/response task
operations. Long-running work is returned as a task and can be followed with
`tasks/get`.

The server supports asynchronous work with `message/send` and
`configuration.blocking: false`, followed by `tasks/get`.

These samples use the A2A v0.3 JSON-RPC names used by the existing samples:
`message/send`, `tasks/get`, and `tasks/cancel`. A client using A2A 1.0 should
send `A2A-Version: 1.0` and use `SendMessage`, `GetTask`, `ListTasks`, and
`CancelTask`; its non-blocking option is `configuration.returnImmediately`.
The server accepts both versions, but streaming is disabled in both.

The sample scripts import `call`, `connect`, `send_prompt`, and
`print_task_summary` from the adjacent
[`_common.py`](https://github.com/oracle/python-select-ai/blob/main/samples/a2a/dynamic/_common.py)
file. This is a
repository-local sample helper, not an additional Python dependency. It sends
the JSON-RPC requests, reads the fields requested by the returned A2UI form,
submits only those fields from the environment variables below, and formats
the final task result. If you copy a script elsewhere, copy
[`_common.py`](https://github.com/oracle/python-select-ai/blob/main/samples/a2a/dynamic/_common.py)
with it or replace those helpers with your own A2A client code.

## Local setup

Install the A2A extra if necessary:

```bash
source .venv/bin/activate
pip install -e '.[a2a]'
```

### Dynamic standalone

This is the smallest complete local setup. Fix the DSN and team on the server
so the generated form contains only username and password. Ensure database
username and password variables are absent from the server process so it does
not select the fixed shared-pool path:

```bash
env -u SELECT_AI_USER -u SELECT_AI_PASSWORD \
  select-ai a2a serve \
  --deployment standalone \
  --host 127.0.0.1 \
  --port 8000 \
  --public-url http://127.0.0.1:8000 \
  --allow-unauthenticated \
  --dsn '<database DSN>' \
  --team ORACLE_AI_DATABASE_AGENT
```

Dynamic standalone keeps its routing in memory and therefore runs as one
server process and one service instance. It does not require Consul or the
separate worker command.

### Clustered

Run these commands in three terminals from the repository root.

Terminal 1, Consul:

```bash
consul agent -dev -bind=127.0.0.1 -client=127.0.0.1
```

Terminal 2, one worker:

```bash
source .venv/bin/activate

select-ai a2a worker \
  --host 127.0.0.1 \
  --port 8081 \
  --consul-url http://127.0.0.1:8500 \
  --worker-id local-worker \
  --worker-endpoint http://127.0.0.1:8081
```

Terminal 3, the dynamic server:

```bash
source .venv/bin/activate

select-ai a2a serve \
  --deployment clustered \
  --host 127.0.0.1 \
  --port 8000 \
  --public-url http://127.0.0.1:8000 \
  --allow-unauthenticated \
  --consul-url http://127.0.0.1:8500
```

For either deployment, export the form values in the terminal that runs the
sample scripts. The helper submits only the properties requested by the
server, so deployment-fixed DSN or team values are not sent back:

```bash
export SELECT_AI_DB_CONNECT_STRING='<database DSN>'
export SELECT_AI_USER='<database user>'
export SELECT_AI_PASSWORD='<database password>'
export SELECT_AI_A2A_TEAM='ORACLE_AI_DATABASE_AGENT'
```

For a TNS-alias DSN, set `TNS_ADMIN` in the worker terminal before starting
the clustered worker, or in the standalone server terminal. Wallet-based
Oracle Database mTLS is not currently supported by the dynamic session path.

To call an authenticated server, set its bearer JWT without changing the
scripts:

```bash
export SELECT_AI_A2A_BEARER_TOKEN='<JWT>'
```

Override the default endpoint with `SELECT_AI_A2A_ENDPOINT`.

## Run the samples

First inspect the exact A2UI artifact and requested fields without submitting
credentials:

```bash
python samples/a2a/dynamic/inspect_form.py
```

The task samples perform the connection-form handshake automatically and
validate that the final artifact is
`database-agent-result`.

Blocking database task:

```bash
python samples/a2a/dynamic/blocking_task.py
```

Non-blocking database task with polling:

```bash
python samples/a2a/dynamic/task_poll.py
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

The worker health endpoint applies only to clustered deployment.
