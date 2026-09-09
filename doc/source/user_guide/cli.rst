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
standalone server, dynamic gateway, internal worker, and Agent Card generator.
RAG is supported when the selected profile is already configured with a vector
index.

.. only:: html

   .. image:: /image/select_ai_cli_demo.gif
      :alt: Select AI CLI demo
      :width: 100%

.. only:: latex

   .. image:: /image/select_ai_cli_demo.png
      :alt: Select AI CLI demo
      :width: 100%

The package provides an optional ``select-ai`` command line tool. Install the
CLI extra to use profile, SQL, chat, and A2A commands. The ``a2a`` extra is an
alias that makes the A2A dependency set explicit:

.. code-block:: bash

    pip install 'select_ai[cli]'
    # Equivalent installation for an A2A deployment:
    pip install 'select_ai[a2a]'

Use ``select-ai --help`` to view the available command groups and
``select-ai <command> --help`` to view options for a specific command.

The complete A2A guide covers the standalone server, dynamic gateway, Agent
Card discovery, A2A protocol compatibility, task execution, persistent
Oracle-backed state, and Google Cloud deployment. See :ref:`A2A Integration
<a2a>`.

Set the database connection details as environment variables, or pass them as
command line options:

.. code-block:: bash

    export SELECT_AI_USER=<db_user>
    export SELECT_AI_PASSWORD=<db_password>
    export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>

Connection options
==================

Database-backed commands accept the following connection options. The
standalone ``select-ai a2a serve`` command uses them directly; the dynamic
gateway receives DSN, username, and password through its A2UI connection form,
and ``a2a worker`` receives those values internally when it opens a session.

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

If ``--password`` and ``SELECT_AI_PASSWORD`` are not set, the CLI prompts for
the database password. Wallet options are optional and apply to database
commands that support wallet connections, including standalone
``select-ai a2a serve``. The dynamic gateway session path currently accepts
only DSN, username, and password.

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
    select-ai a2a gateway --help
    select-ai a2a worker --help
    select-ai a2a agent-card --help

.. list-table:: A2A CLI commands
   :header-rows: 1
   :widths: 34 66
   :align: left

   * - Command
     - Purpose
   * - ``select-ai a2a serve``
     - Start a standalone A2A HTTP server for one configured database AI Agent
       Team. It accepts the database connection and optional wallet options.
   * - ``select-ai a2a gateway``
     - Start the public dynamic A2A/A2UI gateway. It uses Consul to discover
       workers and does not connect to Oracle directly.
   * - ``select-ai a2a worker``
     - Start the internal worker that registers with Consul and creates an
       isolated database-bearing child process for each submitted connection.
   * - ``select-ai a2a agent-card``
     - Print a Gemini Enterprise-compatible A2A v0.3 Agent Card without
       starting a server.

Standalone server
-----------------

Start one configured database AI Agent Team. The team, user, password, and DSN
can be passed as options or through the ``SELECT_AI_*`` environment variables:

.. code-block:: bash

    export SELECT_AI_USER=select_ai_user
    export SELECT_AI_PASSWORD='database-password'
    export SELECT_AI_DB_CONNECT_STRING=db2025adb_medium

    select-ai a2a serve \
        --team ORACLE_AI_DATABASE_AGENT \
        --host 0.0.0.0 \
        --port 8000 \
        --public-url https://a2a.example.com

.. only:: html

   .. image:: /image/select_ai_a2a_server_demo.gif
      :alt: Select AI A2A server CLI demo
      :width: 100%

Important options are ``--team`` (required), ``--host``, ``--port``,
``--public-url``, ``--description``, and ``--pool-max-size``. The
``--wallet-location`` and ``--wallet-password`` options configure an Oracle
wallet for this standalone path. If no password is provided, the command
prompts for it.

Dynamic gateway and worker
--------------------------

The gateway and worker are separate processes. Start a worker for each runtime
that can reach Consul and Oracle, then start the public gateway. The worker has
no database credentials at startup; the gateway opens a temporary session by
passing the A2UI form values to the worker.

.. code-block:: bash

    CONSUL_HTTP_URL=http://127.0.0.1:8500 \
    WORKER_ID=local-worker \
    WORKER_ADDRESS=127.0.0.1 \
    WORKER_PORT=8081 \
    select-ai a2a worker --host 127.0.0.1 --port 8081

    select-ai a2a gateway \
        --host 127.0.0.1 \
        --port 8000 \
        --agent-url http://127.0.0.1:8000 \
        --consul-url http://127.0.0.1:8500

The worker options are ``--host``, ``--port``, ``--session-ttl-seconds``, and
``--session-start-timeout-seconds``. Its registration can be configured with
the ``CONSUL_HTTP_URL``, ``WORKER_ID``, ``WORKER_ADDRESS``, ``WORKER_PORT``,
and optional ``WORKER_ENDPOINT`` environment variables. The worker's
``--tls-cert-file``, ``--tls-key-file``, and ``--tls-ca-file`` options enable
gateway-to-worker mTLS; provide all three together.

The gateway options are ``--agent-url`` (required, or ``AGENT_URL``),
``--consul-url`` (or ``CONSUL_HTTP_URL``), ``--worker-service`` (or
``WORKER_SERVICE``), and ``--session-ttl-seconds`` (or
``SESSION_TTL_SECONDS``). The optional
``--worker-tls-ca-file``, ``--worker-tls-cert-file``, and
``--worker-tls-key-file`` options configure the gateway's client side of
gateway-to-worker mTLS. These TLS settings protect the internal HTTP hop and
are separate from Oracle wallet authentication.

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
     - Start the standalone A2A server.
   * - ``select-ai a2a gateway``
     - Start the public dynamic A2A gateway.
   * - ``select-ai a2a worker``
     - Start the internal dynamic-session worker.
   * - ``select-ai a2a agent-card``
     - Print an A2A v0.3 Agent Card.
