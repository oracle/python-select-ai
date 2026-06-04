.. _cli:

**************************
Command line interface
**************************

.. only:: html

   .. image:: /image/select_ai_cli_demo.gif
      :alt: Select AI CLI demo
      :width: 100%

.. only:: latex

   .. image:: /image/select_ai_cli_demo.png
      :alt: Select AI CLI demo
      :width: 100%

The package provides an optional ``select-ai`` command line tool. Install the
CLI extra to use it:

.. code-block:: bash

    pip install 'select_ai[cli]'

Set the database connection details as environment variables, or pass them as
command line options:

.. code-block:: bash

    export SELECT_AI_USER=<db_user>
    export SELECT_AI_PASSWORD=<db_password>
    export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>

Interactive chat
================

The ``chat`` subcommand starts an interactive profile chat REPL. Pass an
existing Select AI profile with ``--profile``:

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

SQL commands
============

SQL operations are one-shot subcommands instead of a REPL:

.. code-block:: bash

    select-ai sql show --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql run --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql explain --profile OCI_AI_PROFILE "count movies by genre"
    select-ai sql narrate --profile OCI_AI_PROFILE "count movies by genre"

Profile commands
================

Summarize and translate are available under the ``profile`` command group:

.. code-block:: bash

    select-ai profile list
    select-ai profile list --pattern "OCI.*"

    select-ai profile summarize --profile OCI_AI_PROFILE "Text to summarize"
    select-ai profile summarize --profile OCI_AI_PROFILE --file notes.txt

    select-ai profile translate \
        --profile OCI_AI_PROFILE \
        --source-language English \
        --target-language German \
        "Thank you"
