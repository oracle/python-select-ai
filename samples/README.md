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
  supervised-team samples.

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

To compare it with the default blocking behavior, run:

```bash
python samples/a2a/blocking_task.py
```

This sample intentionally omits `configuration.blocking`. The server waits
for the database work to finish and returns the completed Task in the initial
`message/send` response; no polling is needed.

## A2A dynamic gateway

The dynamic gateway samples submit the A2UI database connection form, open a
temporary worker session, and execute database tasks. The gateway advertises
`streaming: false` and supports non-blocking task execution with
`configuration.blocking: false` and `tasks/get`.

Gateway-specific samples that perform the form handshake and then execute a
real database task are in [a2a/gateway](a2a/gateway/README.md):

```bash
python samples/a2a/gateway/blocking_task.py
python samples/a2a/gateway/task_poll.py
```

See that README for local Consul, worker, and gateway startup instructions.


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
