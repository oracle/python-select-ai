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
