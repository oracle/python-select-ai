.. _conn:

*****************************
Connecting to Oracle Database
*****************************

``select_ai`` uses the Python thin driver i.e. ``python-oracledb``
to connect to the database and execute PL/SQL subprograms.

The library keeps the active connection or connection pool for the current
process so profile, credential, provider, vector index, and agent APIs can use
it without passing a connection object to each call. Use a standalone
connection for scripts and notebooks. Use a connection pool for applications
that handle concurrent work, such as web services or worker processes.

Most samples read connection values from environment variables:

.. code-block:: sh

   export SELECT_AI_USER=<db_user>
   export SELECT_AI_PASSWORD=<db_password>
   export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>

Then the Python code can load those values:

.. code-block:: python

   import os
   import select_ai

   user = os.getenv("SELECT_AI_USER")
   password = os.getenv("SELECT_AI_PASSWORD")
   dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

   select_ai.connect(user=user, password=password, dsn=dsn)

.. _sync_conn:

Synchronous connection
======================

To connect to an Oracle Database synchronously, use
``select_ai.connect()`` as shown below:

.. code-block:: python

   import select_ai

   user = "<your_db_user>"
   password = "<your_db_password>"
   dsn = "<your_db_dsn>"
   select_ai.connect(user=user, password=password, dsn=dsn)

Close a standalone synchronous connection with ``select_ai.disconnect()``:

.. code-block:: python

   select_ai.disconnect()

.. _async_conn:

Asynchronous connection
=======================

Asynchronous applications should use ``select_ai.async_connect()`` along
with ``await`` keyword:

.. code-block:: python

   import select_ai

   user = "<your_db_user>"
   password = "<your_db_password>"
   dsn = "<your_db_dsn>"
   await select_ai.async_connect(user=user, password=password, dsn=dsn)

Close a standalone asynchronous connection with
``await select_ai.async_disconnect()``:

.. code-block:: python

   await select_ai.async_disconnect()


Connection Pool
===============

You can create a connection pool using the ``select_ai.create_pool``
and ``select_ai.create_pool_async`` methods. After a pool is created, these
methods configure Select AI operations to acquire and release connections from
the pool for each operation.

.. code-block:: python

   import select_ai

   user = "<your_db_user>"
   password = "<your_db_password>"
   dsn = "<your_db_dsn>"

   # for sync pool
   select_ai.create_pool(
       user=user,
       password=password,
       dsn=dsn,
       min_size=5,
       max_size=10,
       increment=5
   )

   # for async pool
   select_ai.create_pool_async(
       user=user,
       password=password,
       dsn=dsn,
       min_size=5,
       max_size=10,
       increment=5
   )

Close a synchronous pool with ``select_ai.disconnect()`` and an asynchronous
pool with ``await select_ai.async_disconnect()``.

Create one pool per process. In multi-process deployments, each process creates
its own pool, so total database connections can grow quickly. Size pools based
on request concurrency and database capacity.

Use pooling for:

* Web applications and API services.
* Worker processes that handle multiple prompts.
* Concurrent prompt processing.
* Long-running applications that should avoid opening a new database connection
  for every request.

Use a standalone connection for:

* Short scripts.
* Local examples.
* One-off administration tasks.

Check this `blog <https://blogs.oracle.com/machinelearning/boosting-select-ai-for-python-concurrency-with-connection-pooling>`__
which shows the benefit of connection pooling with a FastAPI service.

Connection health
=================

Use ``select_ai.is_connected()`` or ``await select_ai.async_is_connected()``
to check whether the current connection or pool is available:

.. code-block:: python

   if not select_ai.is_connected():
       select_ai.connect(user=user, password=password, dsn=dsn)

.. code-block:: python

   if not await select_ai.async_is_connected():
       await select_ai.async_connect(user=user, password=password, dsn=dsn)

Wallet connections
==================

.. note::

   For m-TLS (wallet) based connections, additional parameters like
   ``wallet_location``, ``wallet_password``, ``config_dir``, ``https_proxy``,
   and ``https_proxy_port`` can be passed to ``connect``, ``async_connect``,
   ``create_pool``, and ``create_pool_async``.

For example:

.. code-block:: python

   select_ai.connect(
       user=user,
       password=password,
       dsn=dsn,
       wallet_location="/path/to/wallet",
       config_dir="/path/to/wallet",
       wallet_password="<wallet_password>",
   )

The same keyword arguments can be used with ``async_connect`` and the pool
creation APIs.
