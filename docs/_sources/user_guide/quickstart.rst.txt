.. _first-query:

************************
Run your first SQL query
************************

This walkthrough creates a temporary table with three rows, stores an OpenAI
API key in a temporary database credential, creates a Select AI profile, and
queries the table using natural language. It removes its table, credential,
and profile when finished. Use a development database account.

Requests use the API key in ``OPENAI_API_KEY`` on each run. Existing database
credentials are not used or replaced. OpenAI API usage is billed separately
from ChatGPT and Codex subscriptions.

Install and configure Python
============================

Use Python 3.11 through 3.14 and an Oracle Database environment with
``DBMS_CLOUD_AI`` available. See :ref:`Compatibility <compatibility>` for
feature-specific requirements.

.. code-block:: bash

   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install 'select_ai==1.5.0'

On Windows, use the virtual-environment activation command in
:ref:`Installation <installation>`.

Set the following values in your shell. Choose an OpenAI model supported by
your database integration and available to your API project:

.. code-block:: bash

   export SELECT_AI_USER='your_database_user'
   export SELECT_AI_PASSWORD='your_database_password'
   export SELECT_AI_DB_CONNECT_STRING='your_database_connect_string'
   export OPENAI_API_KEY='your_api_key'
   export SELECT_AI_MODEL='gpt-4.1'

To try a different key, replace ``OPENAI_API_KEY`` and rerun the script. Keep
keys out of source files and version control. OCI-specific environment
variables are not read by this sample.

For wallet connections, add the parameters described in
:ref:`Wallet connections <user_guide/connection:Wallet connections>` to the
sample's ``connect()`` call. Do not commit secrets to the repository.

Prepare the database account
============================

A database administrator must grant the application user Select AI package
privileges and outbound HTTP access to ``api.openai.com``. Pass ``--setup`` to
perform both steps before running the example. Set the administrator variables
in addition to the application and OpenAI variables above:

.. code-block:: bash

   export SELECT_AI_ADMIN_USER='your_database_admin_user'
   export SELECT_AI_ADMIN_PASSWORD='your_database_admin_password'
   python samples/quickstart.py --setup

The script connects as the administrator, calls ``grant_privileges()`` and
``grant_network_access(users=..., host="api.openai.com", privileges="http")``,
commits the setup, and disconnects. It then connects as the application user
and runs the example. The administrator must be allowed to grant package
privileges and manage network ACLs. Administrator and application connections
use the same DSN; add required wallet arguments to both connection calls.

Run setup once for each application user/database. For later runs, omit the
flag; administrator credentials are then unnecessary:

.. code-block:: bash

   python samples/quickstart.py

The grants remain after the temporary sample objects are removed. See
:ref:`Privileges <privileges>` to revoke package or network privileges later.

The application account must also have ``CREATE SESSION``, ``CREATE TABLE``,
and sufficient tablespace quota to create the temporary table. Have the
administrator assign an appropriate quota in the account's default tablespace.
The helper does not grant these privileges or quota. The sample does not
create a public credential synonym and does not require ``CREATE PUBLIC
SYNONYM``.

Run the example
===============

Save the following as ``quickstart.py``, or run
``python samples/quickstart.py`` from a repository checkout:

.. literalinclude:: ../../../samples/quickstart.py
   :language: python
   :start-at: import argparse

The script prints generated SQL and a DataFrame containing a count of three.
Table names include a generated suffix. SQL formatting and the model's chosen
column label may vary; representative result output is:

.. code-block:: text

      ITEM_COUNT
   0           3

The profile's ``object_list`` includes the sample table using the schema name
resolved from the database connection. Other profile attributes use their
defaults, including object-list enforcement. The object list supplies metadata
for SQL generation; database privileges determine which objects the user can
access. See :ref:`Profile attributes <profile_attributes>` for explicit
enforcement settings.

``show_sql()`` generates SQL without executing it. ``run_sql()`` makes a
separate generation request and executes that response; it does not execute
the SQL string returned by the earlier call. In applications that require
approval of an exact statement, review the generated statement and execute
that approved statement through your database API.

If connection fails, check the DSN, password, and wallet settings. For package
or network authorization failures, return to the administrator setup. For
model or provider errors, check the API key, model access, API billing, and
project limits. See :ref:`Error handling <error-handling>` for Python exception
handling. The sample's cleanup removes only objects it successfully created;
administrator grants remain in place for subsequent workflows.

Waiting and timeouts
====================

The script prints progress before connecting, creating objects, and requesting
SQL from OpenAI. If it waits at ``Generating SQL with OpenAI...``, the
database is processing the model request. Missing network ACL privileges usually raise
an authorization error; waiting alone does not prove that the ACL is missing.
Check database egress, provider availability, API billing, and project limits.
HTTP 429 can indicate quota or rate limits; retries may extend the wait.

The sample sets ``tcp_connect_timeout=15`` for connection establishment and
``connection.call_timeout=120_000`` for database calls. The latter is in
milliseconds and limits each database round trip, rather than total script
runtime. Increase it deliberately for slower requests. See the
`driver timeout documentation
<https://python-oracledb.readthedocs.io/en/stable/api_manual/connection.html#oracledb.Connection.call_timeout>`__.
