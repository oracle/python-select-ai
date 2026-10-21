.. _cli:

**************************
Command line interface
**************************

The ``select-ai`` command line interface (CLI) provides a terminal workflow for
using Select AI profiles without writing Python code. It is intended for quick
exploration, profile validation, prompt testing, SQL generation,
summarization, translation, and interactive chat against an existing profile.

The CLI is useful for developers who want a fast shell workflow and for
non-developers who are comfortable running terminal commands but do not want to
write Python code. It can help users check whether a profile is configured
correctly, inspect generated SQL, try prompts during development, or interact
with a curated profile through a simple command.

The CLI works with Select AI profiles and can also run the Select AI A2A
server, clustered gateway and worker, and Agent Card generator. RAG is
supported when the selected profile is already configured with a vector
index. The :ref:`A2A guide <a2a>` explains the difference between fixed and
dynamic connections and standalone and clustered topologies; this page gives
the corresponding CLI commands.

.. only:: html

   .. image:: /image/select_ai_cli_demo.gif
      :alt: Select AI CLI demo
      :width: 100%

.. only:: latex

   .. image:: /image/select_ai_cli_demo.png
      :alt: Select AI CLI demo
      :width: 100%

The package provides an optional ``select-ai`` command line tool. Install the
CLI extra to use profile, SQL, and chat commands. Install the separate ``a2a``
extra for the A2A server and worker commands. If A2A dependencies are missing,
invoking the A2A command group or a server or worker command reports how to
install them; the other CLI commands remain available:

.. code-block:: bash

    pip install 'select_ai[cli]'
    # Install A2A support:
    pip install 'select_ai[a2a]'

Use ``select-ai --help`` to view the available command groups and
``select-ai <command> --help`` to view options for a specific command.

The A2A examples below pass database credentials with CLI options so the
commands are easy to copy and adapt. Environment-variable equivalents are
listed in the connection-options table.

Connection options
==================

Database-backed commands accept the following connection options. The
``select-ai a2a serve`` command accepts these options directly. In standalone
mode, providing all four connection values at startup selects the fixed
connection path; omitting values opens a dynamic A2UI form for them. In
clustered mode, the gateway can preconfigure any values and the form collects
the rest. The worker receives the resolved values when it opens a session.
For a private database CA, use ``--database-tls-ca-file``; the CLI reads PEM
from the specified file.

.. list-table:: Connection options
   :header-rows: 1
   :widths: 30 70
   :align: left

   * - Option
     - Environment variable
   * - ``--user``
     - ``SELECT_AI_USER``
   * - ``--password``
     - ``SELECT_AI_PASSWORD``
   * - ``--dsn``
     - ``SELECT_AI_DB_CONNECT_STRING``
   * - ``--wallet-location``
     - ``SELECT_AI_WALLET_LOCATION``
   * - ``--wallet-password``
     - ``SELECT_AI_WALLET_PASSWORD``
   * - ``--database-tls-ca-file``
     - ``SELECT_AI_DATABASE_TLS_CA_FILE``

Profile, SQL, and chat commands prompt for the database password when neither
``--password`` nor ``SELECT_AI_PASSWORD`` is set. For ``a2a serve``, omitting
any connection value selects dynamic mode, and the A2A client supplies the
missing values through an A2UI form. Supply ``--dsn``, ``--user``,
``--password``, and ``--team`` for fixed standalone mode. Wallet options apply
to fixed standalone A2A connections; dynamic sessions do not currently
support Oracle wallet authentication. The A2A CLI examples below include a
host, port, service name, credentials, and optional database CA file.

Interactive chat
================

The ``chat`` subcommand starts an interactive profile chat
Read-Eval-Print Loop (REPL). A REPL is a terminal session that reads each
prompt you type, evaluates it, prints the response, and then waits for the next
prompt. Pass an existing Select AI profile with ``--profile``:

.. code-block:: bash

    select-ai chat --profile OCI_AI_PROFILE

The REPL uses ``Profile.chat_session()`` so prompts in the same terminal session
share conversation context. Responses stream by default. Use ``--no-stream`` to
print each response after it is fully generated.

.. code-block:: text

    Connected to Select AI profile: OCI_AI_PROFILE
    Type /help for commands. Type /exit to quit.
    select_ai> What tables can I ask about?
    ...
    select_ai> /exit

Useful options:

- ``--user``, ``--password``, and ``--dsn`` override the environment values.
- ``--wallet-location`` and ``--wallet-password`` configure wallet connections.
- ``--chunk-size`` controls the number of CLOB characters read per stream chunk.
- ``--conversation-length`` controls how many prompts are retained in context.
- ``--keep-conversation`` keeps the database conversation after the REPL exits.

Inside the REPL, use these commands:

.. list-table:: Chat REPL commands
   :header-rows: 1
   :widths: 25 75
   :align: left

   * - Command
     - Description
   * - ``/help``
     - Show available REPL commands.
   * - ``/clear``
     - Start a fresh database conversation.
   * - ``/exit``
     - Exit the chat session.
   * - ``/quit``
     - Exit the chat session.

SQL commands
============

SQL operations are one-shot subcommands instead of a REPL:

.. code-block:: bash

    select-ai sql show --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql run --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql explain --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql narrate --profile OCI_AI_PROFILE "count movies by genre"

``show``, ``explain``, and ``narrate`` stream text output by default. Use
``--no-stream`` to print the response after it is fully generated, and
``--chunk-size`` to control the number of CLOB characters read per stream
chunk.

``run`` executes the generated SQL and prints the returned result table. It
does not support streaming.

Profile commands
================

Summarize and translate are available under the ``profile`` command group:

.. code-block:: bash

    select-ai profile list
    select-ai profile list --pattern "OCI.*"

    select-ai profile summarize --profile OCI_AI_PROFILE "Text to summarize"
    select-ai profile summarize --profile OCI_AI_PROFILE --file notes.txt
    select-ai profile summarize \
        --profile OCI_AI_PROFILE \
        --location-uri https://example.com/article.txt
    select-ai profile summarize \
        --profile OCI_AI_PROFILE \
        --location-uri https://objectstorage.example.com/n/namespace/b/bucket/o/file.txt \
        --credential-name OBJECT_STORE_CRED

    select-ai profile translate \
        --profile OCI_AI_PROFILE \
        --source-language English \
        --target-language German \
        "Thank you"

``profile list`` prints profile names visible to the connected database user.
Use ``--pattern`` to filter names with a regular expression.

``profile summarize`` accepts one content source at a time: inline text,
``--file``, or ``--location-uri``. Use ``--prompt`` to guide the summary and
``--credential-name`` when the location URI requires an object storage
credential.

A2A commands
============

The ``a2a`` command group exposes the cloud-neutral A2A runtimes. Use
``select-ai a2a --help`` or a command-specific ``--help`` option to see the
current defaults:

.. code-block:: bash

    select-ai a2a --help
    select-ai a2a serve --help
    select-ai a2a worker --help
    select-ai a2a agent-card --help

.. list-table:: A2A CLI commands
   :header-rows: 1
   :widths: 34 66
   :align: left

   * - Command
     - Purpose
   * - ``select-ai a2a serve``
     - Start the public A2A HTTP server. The default standalone topology needs
       no worker or Consul. Add ``--deployment clustered`` to use a gateway,
       workers, and Consul.
   * - ``select-ai a2a worker``
     - Start an internal database worker for clustered topology. Standalone
       topology does not use this command.
   * - ``select-ai a2a agent-card``
     - Print a Gemini Enterprise-compatible A2A v0.3 Agent Card without
       starting a server.

.. _a2a-cli-examples:

A2A deployment examples
-----------------------

The :ref:`A2A guide <a2a>` explains how fixed and dynamic connections differ
from standalone and clustered topologies. These examples use CLI options for
the database settings. Replace the placeholder credentials and connection
string with your values.

Fixed standalone connection
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass all four connection values at startup to use the standalone server's
shared connection pool. This needs no Consul or worker and supports streaming:

.. code-block:: bash

    select-ai a2a serve \
        --deployment standalone \
        --team ORACLE_AI_DATABASE_AGENT \
        --user DB_USERNAME \
        --password 'DB_PASSWORD' \
        --dsn 'dbhost.example.com:1521/db_service' \
        --database-tls-ca-file /run/secrets/database-ca.pem \
        --database-call-timeout-seconds 120 \
        --host 0.0.0.0 \
        --port 8000 \
        --public-url https://a2a.example.com

The database CA file is optional when the server certificate is already
trusted by the operating system. ``--wallet-location`` and
``--wallet-password`` are also available for fixed standalone connections
that use an Oracle wallet.

.. only:: html

   .. image:: /image/select_ai_a2a_server_demo.gif
      :alt: Select AI A2A server CLI demo
      :width: 100%

Dynamic standalone connection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Omit one or more of ``--dsn``, ``--user``, ``--password``, and ``--team`` to
have the A2A client supply those values through an A2UI form. The server runs
the session child processes itself, so this mode needs no Consul or separate
worker. Run a single Uvicorn process. Dynamic standalone supports task polling,
not streaming:

.. code-block:: bash

    select-ai a2a serve \
        --deployment standalone \
        --database-tls-ca-file /run/secrets/database-ca.pem \
        --host 0.0.0.0 \
        --port 8000 \
        --public-url https://a2a.example.com

Remove ``--database-tls-ca-file`` when the database server certificate is
already trusted by the operating system. Any connection values provided on
the command line are fixed; the form asks only for the values that are
missing.

Clustered gateway and worker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clustered topology requires Consul and at least one worker. The gateway can
run without database credentials; by default, the A2A client supplies them
through the connection form. For local development, start Consul and then run
the worker and gateway in separate terminals:

.. code-block:: bash

    # Terminal 1: local development Consul agent
    consul agent -dev -bind=127.0.0.1 -client=127.0.0.1

    # Terminal 2: database worker
    select-ai a2a worker \
        --host 127.0.0.1 \
        --port 8081 \
        --consul-url http://127.0.0.1:8500 \
        --worker-id local-worker \
        --worker-endpoint http://127.0.0.1:8081 \
        --database-call-timeout-seconds 120

    # Terminal 3: public gateway
    select-ai a2a serve \
        --deployment clustered \
        --host 127.0.0.1 \
        --port 8000 \
        --public-url http://127.0.0.1:8000 \
        --consul-url http://127.0.0.1:8500 \
        --database-tls-ca-file /run/secrets/database-ca.pem \
        --database-call-timeout-seconds 120

The local Consul command is for development only. In a deployment, point the
gateway and workers at the existing Consul service and use network-reachable
worker addresses. The database CA option is needed only for a private database
CA; the gateway passes its PEM contents to the worker when opening a session.
Set the same ``--database-call-timeout-seconds`` value on the gateway and
worker. See the A2A guide for Consul setup and clustered deployment details.

Important ``serve`` options include ``--team``, ``--host``, ``--port``,
``--public-url``, ``--description``, ``--pool-max-size``, and
``--database-call-timeout-seconds``. The default database call timeout is 120
seconds. On the clustered gateway, this value sets the request deadline basis;
the worker applies it to Oracle calls and derives its child-process deadline.

By default, ``a2a serve`` does not require an application OAuth token. A2A
task and context records use the shared anonymous owner, and each A2A context
maps to its own Select AI conversation. Add ``--require-oauth`` to require
``Authorization: Bearer ...`` and scope those records by authenticated owner
as well as context. The Agent Card advertises bearer security only in that
mode.

Clustered option reference
~~~~~~~~~~~~~~~~~~~~~~~~~~

The worker options are ``--host``, ``--port``, ``--worker-id``,
``--consul-url``, ``--worker-endpoint``, ``--session-ttl-seconds``,
``--conversation-retention-days``, ``--session-start-timeout-seconds``, and
``--database-call-timeout-seconds``.
``WORKER_ID``, ``CONSUL_HTTP_URL``, ``WORKER_ENDPOINT``, and
``CONVERSATION_RETENTION_DAYS`` are environment fallbacks; explicit
command-line values take precedence. Conversation retention defaults to 7 days;
use 0 to keep conversations until manually deleted. ``--port`` is also the
port registered with Consul. Cluster manifests can set ``WORKER_ADDRESS`` to
the pod IP when no endpoint is supplied. The worker's ``--tls-cert-file``,
``--tls-key-file``, and
``--tls-ca-file`` options enable gateway-to-worker mTLS; provide all three
together.

The clustered serve options are ``--public-url`` (or ``PUBLIC_URL``),
``--consul-url`` (or ``CONSUL_HTTP_URL``), ``--worker-service`` (or
``WORKER_SERVICE``), and ``--session-ttl-seconds`` (or
``SESSION_TTL_SECONDS``). ``--dsn``, ``--user``, ``--password``, and ``--team``
fix any supplied connection values; the generated A2UI form contains only the
missing values. ``--a2ui-form`` loads a custom A2UI JSON form that must submit
exactly those missing values. ``--require-oauth`` has the same ownership
behavior in standalone and clustered deployments. The optional
``--worker-tls-ca-file``, ``--worker-tls-cert-file``, and
``--worker-tls-key-file`` options configure the gateway's client side of
gateway-to-worker mTLS. These TLS settings protect the internal HTTP hop and
are separate from the database CA configured with
``--database-tls-ca-file`` and from Oracle wallet authentication.
The gateway and worker must use the same ``--database-call-timeout-seconds``
value. It defaults to 120 seconds; the worker and gateway derive their request
deadlines from this database call timeout.

Agent Card generation
---------------------

Print the portable A2A v0.3 card for a standalone public service:

.. code-block:: bash

    select-ai a2a agent-card \
        --team ORACLE_AI_DATABASE_AGENT \
        --public-url https://a2a.example.com

``--team`` and ``--public-url`` are required; use ``--description`` to replace
the default description. See :ref:`A2A Integration <a2a>` for protocol
compatibility, persistent state, gateway session behavior, wallet support, and
Google Cloud deployment details.

Command summary
===============

.. list-table:: CLI command summary
   :header-rows: 1
   :widths: 35 65
   :align: left

   * - Command
     - Purpose
   * - ``select-ai chat``
     - Start an interactive context-aware chat session.
   * - ``select-ai sql show``
     - Generate SQL without executing it.
   * - ``select-ai sql run``
     - Generate SQL, execute it, and print the result table.
   * - ``select-ai sql explain``
     - Explain generated SQL.
   * - ``select-ai sql narrate``
     - Generate and execute SQL, then return a natural language answer.
   * - ``select-ai profile list``
     - List saved profile names.
   * - ``select-ai profile summarize``
     - Summarize inline content, a file, or a URI.
   * - ``select-ai profile translate``
     - Translate text with a saved profile.
   * - ``select-ai a2a serve``
     - Start the public A2A server. The default is standalone; use
       ``--deployment clustered`` for a gateway and workers. Omitted
       connection values are collected through A2UI.
   * - ``select-ai a2a worker``
     - Start a database worker for clustered topology. Standalone deployments
       do not use a worker.
   * - ``select-ai a2a agent-card``
     - Print an A2A v0.3 Agent Card.
