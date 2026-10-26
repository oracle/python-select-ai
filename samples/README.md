# select_ai samples

This directory contains samples for python-select-ai. To run the scripts,
define and export the following environment variables

```dotenv
export SELECT_AI_ADMIN_USER=<db_admin>
export SELECT_AI_ADMIN_PASSWORD=<db_admin_password>
export SELECT_AI_USER=<select_ai_db_user>
export SELECT_AI_PASSWORD=<select_ai_db_password>
export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>
export TNS_ADMIN=<path/to/dir_containing_tnsnames.ora>
```

> Note: In production, do not save secrets in environment variables

> `SELECT_AI_ADMIN_USER` and `SELECT_AI_ADMIN_PASSWORD` are needed only to
> grant privileges to regular user. They are used in 2 sample scripts
> `enable_ai_provider.py` and `disable_ai_provider.py`

Some of the new samples use this optional environment variable:

- `SELECT_AI_PROFILE_NAME` — existing profile for the conversation and
  supervised-team, profile lifecycle, translation, and request-attribute
  samples.
- `SELECT_AI_SHARE_GRANTEE` — database user or role used by the sharing
  sample.
- `SELECT_AI_OWNER`, `SELECT_AI_VECTOR_INDEX_NAME`, `SELECT_AI_TEAM_NAME`, and
  `SELECT_AI_CREDENTIAL_NAME` — optional names used by the sharing sample.

## Cloud provider profiles

Create a profile and run a test chat against one of the supported cloud AI
providers:

```bash
export AWS_ACCESS_KEY_ID=<aws_access_key>
export AWS_SECRET_ACCESS_KEY=<aws_secret_key>
python samples/profile_create_aws.py

export AZURE_API_KEY=<azure_api_key>
python samples/profile_create_azure.py

export GOOGLE_API_KEY=<google_api_key>
python samples/profile_create_gcp.py
```

The scripts create or replace the provider credential and profile, grant the
database user's HTTP access to the provider endpoint, and print a test chat
response. See the
[provider documentation](../doc/source/user_guide/provider.rst#cloud-provider-profile-samples)
for the provider settings and representative output.

## Supervised agent teams

Create a team with a dedicated supervisor agent, run a prompt through the
supervisor workflow, and inspect the database-generated supervisor task:

```bash
python samples/agent/team_supervisor_inspect.py
python samples/agent/async/team_supervisor_inspect.py
```

The samples set `AgentAttributes(supervisor=True)` on the coordinating agent
and pass that agent's name as `TeamAttributes.supervisor_agent`. The database
populates `supervisor_task` when the team is created.

## Agent definitions and tool inspection

Retrieve a canonical database definition:

```bash
python samples/agent/get_definition.py
python samples/agent/async/get_definition.py
```

Inspect and directly invoke a PL/SQL tool:

```bash
python samples/agent/tool_run_describe.py
python samples/agent/async/tool_run_describe.py
```

The supervised-team samples above also demonstrate
`Team.describe_team()`/`AsyncTeam.describe_team()` and
`Team.list_tools()`/`AsyncTeam.list_tools()`.

## Agent execution history

Inspect the latest team execution and its related task and tool history:

```bash
python samples/agent/history_list.py
python samples/agent/async/agent_history_list.py
```

The async sample uses `AsyncTeamHistory`, `AsyncTaskHistory`, and
`AsyncToolHistory` with async iteration.

## Profile lifecycle controls

Disable and re-enable an existing profile without deleting it:

```bash
python samples/profile_enable_disable.py
python samples/async/profile_enable_disable.py
```

The scripts use `SELECT_AI_PROFILE_NAME` when set; otherwise they use the
sample profile name `oci_ai_profile`.

## Translation language defaults

Translate text while letting the provider detect the source language:

```bash
python samples/profile_translate.py
python samples/async/profile_translate.py
```

These samples use `SELECT_AI_PROFILE_NAME` when set and pass only the target
language at the call site. The default profile names are `oci_ai_profile` for
the synchronous sample and `async_oci_ai_profile` for the asynchronous sample.
Profile-level language defaults can be configured with `ProfileAttributes` when
the target is also omitted.

## Request-level profile attribute overrides

Override profile attributes for one request without changing the saved profile:

```bash
python samples/profile_request_attributes.py
python samples/async/profile_request_attributes.py
```

The samples demonstrate `additional_instructions`, integer `seed`, and source
and target language settings passed through the `attributes` mapping.

## Sharing and ownership

Inspect owner-qualified profiles and vector indexes and grant/revoke access to
profiles, vector indexes, teams, and credentials:

```bash
python samples/sharing.py
python samples/async/sharing.py
```

Set `SELECT_AI_SHARE_GRANTEE` before running the scripts. The objects must
already exist, and the scripts should run as their owner. The credential
creation and deletion samples also create and remove a public synonym.

## Conversation prompt history and tags

Create a conversation, list its stored prompts, delete a prompt, and manage
conversation tags:

```bash
python samples/conversation_prompts_tags.py
python samples/async/conversation_prompts_tags.py
```

The scripts use `SELECT_AI_PROFILE_NAME` when set; otherwise they use the
sample profile name `oci_ai_profile`. See the conversation user guide for
representative output.

## A2A non-blocking task polling

Start a Select AI A2A server before running these samples:

```bash
select-ai a2a serve --team ORACLE_AI_DATABASE_AGENT --port 8000
```

After starting a local A2A server, run the fixed sales-analysis prompt as a
non-blocking task and poll it until completion:

```bash
python samples/a2a/task_poll.py
```

The sample sends the A2A v0.3 `message/send` request with
`configuration.blocking: false`, prints the returned task ID, and polls
`tasks/get`. Edit `ENDPOINT` or `PROMPT` at the top of the script if needed.

Representative output is:

```text
Task 42b...: submitted
Task 42b...: working
Task 42b...: completed
{
  "id": "42b...",
  "status": {"state": "completed", "timestamp": "..."},
  "artifacts": [{"name": "database-agent-result", "parts": ["..."]}]
}
```

Task IDs, timestamps, and database answers vary between runs.

To compare it with the default blocking behavior, run:

```bash
python samples/a2a/blocking_task.py
```

This sample intentionally omits `configuration.blocking`. The server waits
for the database work to finish and returns the completed Task in the initial
`message/send` response; no polling is needed.

Representative output is:

```text
Task 7e1...: completed
{
  "id": "7e1...",
  "status": {"state": "completed", "timestamp": "..."},
  "artifacts": [{"name": "database-agent-result", "parts": ["..."]}]
}
```

## Dynamic A2A sessions

The dynamic session samples submit the A2UI database connection form, open a
temporary database session, and execute database tasks. The server advertises
`streaming: false` and supports non-blocking task execution with
`configuration.blocking: false` and `tasks/get`.

Dynamic-session samples that perform the form handshake and then execute a
real database task are in [a2a/dynamic](a2a/dynamic/README.md):

```bash
python samples/a2a/dynamic/blocking_task.py
python samples/a2a/dynamic/task_poll.py
```

See that README for standalone and clustered startup instructions.

The full A2A architecture, protocol details, session lifecycle, and Google
Cloud deployment explanation are in the
[A2A user guide](../doc/source/user_guide/a2a.rst).


`SELECT_AI_DB_CONNECT_STRING` can be in any one of the following formats

- TNS alias

    ```bash
    export SELECT_AI_DB_CONNECT_STRING=db2025adb_medium
    ```

    Ensure there is an entry in `$TNS_ADMIN/tnsnames.ora` mapping to the connect descriptor

    ```bash
    >> tnsnames.ora

    db2025adb_medium = (description= (retry_count=20)(retry_delay=3)
                       (address=(protocol=tcps)(port=1521)(host=adb.<region>.oraclecloud.com))
                       (connect_data=(service_name=db2025adb_medium.adb.oraclecloud.com))
                       (security=(ssl_server_dn_match=yes)))
    ```



- Complete connect string

    ```bash
    export SELECT_AI_DB_CONNECT_STRING="(description= (retry_count=20)(retry_delay=3)
    (address=(protocol=tcps)(port=1521)(host=adb.<region>.oraclecloud.com))
    (connect_data=(service_name=db2025adb_medium.adb.oraclecloud.com))
    (security=(ssl_server_dn_match=yes)))"

    ```

- Simplified connect string

    ```bash
    export SELECT_AI_DB_CONNECT_STRING="tcps://adb.<region>.oraclecloud.com:1521/db2025adb_medium.adb.oraclecloud.com?retry_count=2&retry_delay=3"
    ```

## First query and document RAG

Run `python samples/quickstart.py` after completing the administrator setup in
[Run your first SQL query](../doc/source/user_guide/quickstart.rst).
Set `OPENAI_API_KEY`, `SELECT_AI_MODEL` (for example `gpt-4.1`), and the common
database connection variables. Each run creates a temporary credential from
that environment variable; replace `OPENAI_API_KEY` to try a different key.
Existing database credentials are not changed.

To grant package privileges and OpenAI HTTP access first, set
`SELECT_AI_ADMIN_USER` and `SELECT_AI_ADMIN_PASSWORD`, then run
`python samples/quickstart.py --setup`. It disconnects the administrator before
running as the application user. Subsequent runs do not need `--setup`.
The script removes its temporary table, profile, and credential, prints progress,
and sets a 120-second timeout per database round trip.

For RAG, upload [refund-policy.txt](data/refund-policy.txt) to your object store.
Set `SELECT_AI_DOCUMENT_URI` to that object's URI and
`SELECT_AI_OBJECT_STORAGE_CREDENTIAL` to a database credential that can read it.
The provider credential defaults to `my_oci_ai_profile_key`; override it with
`SELECT_AI_PROVIDER_CREDENTIAL`. See the [vector-index guide](../doc/source/user_guide/vector_index.rst)
for region and model settings before running:

```bash
python samples/vector_index_create.py
python samples/vector_index_rag.py
# Or use the async workflow in its own schema:
python samples/async/vector_index_create.py
python samples/async/vector_index_rag.py
```

These workflows replace `test_vector_index` and their named RAG profiles, and
leave them available after closing the connection. Delete the sample index and
profile when finished. The policy answer should give a 30-calendar-day refund
window; model wording can vary.
