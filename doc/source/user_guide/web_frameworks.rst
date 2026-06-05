.. _web_frameworks:

**************************************************
Using ``select_ai`` with Python web frameworks
**************************************************

Python web applications should create a Select AI connection pool when the
application starts and close it when the application shuts down. A pool lets
concurrent requests share a bounded set of database connections instead of
creating standalone connections per request.

This pattern works with Python WSGI and ASGI frameworks. FastAPI is used below
as a concrete example, but the same approach applies to frameworks such as
Flask, Django, Starlette, Sanic, and Quart: initialize the pool during
application startup, use ``select_ai`` APIs inside request handlers, and close
the pool during application shutdown.

For background and concurrency measurements, see this
`connection pooling blog <https://blogs.oracle.com/machinelearning/boosting-select-ai-for-python-concurrency-with-connection-pooling>`__.

Install dependencies
====================

Install ``select_ai`` and FastAPI server dependencies:

.. code-block:: sh

   python -m pip install select_ai fastapi uvicorn

For local development, set the database connection details as environment
variables:

.. code-block:: sh

   export SELECT_AI_USER=<select_ai_db_user>
   export SELECT_AI_PASSWORD=<select_ai_db_password>
   export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>
   export SELECT_AI_POOL_MIN=5
   export SELECT_AI_POOL_MAX=10
   export SELECT_AI_POOL_INCREMENT=5

If you use an mTLS wallet, also set ``TNS_ADMIN`` or pass wallet parameters to
``select_ai.create_pool()`` / ``select_ai.create_pool_async()``.

FastAPI synchronous endpoints
=============================

Create a file named ``app.py``:

.. code-block:: python

   import os
   from contextlib import asynccontextmanager

   from fastapi import FastAPI

   import select_ai

   user = os.getenv("SELECT_AI_USER")
   password = os.getenv("SELECT_AI_PASSWORD")
   dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

   pool_min = int(os.getenv("SELECT_AI_POOL_MIN", "5"))
   pool_max = int(os.getenv("SELECT_AI_POOL_MAX", "10"))
   pool_increment = int(os.getenv("SELECT_AI_POOL_INCREMENT", "5"))


   @asynccontextmanager
   async def lifespan(app: FastAPI):
       select_ai.create_pool(
           user=user,
           password=password,
           dsn=dsn,
           min_size=pool_min,
           max_size=pool_max,
           increment=pool_increment,
       )
       yield
       select_ai.disconnect()


   app = FastAPI(lifespan=lifespan)


   @app.get("/chat")
   def chat(prompt: str):
       profile = select_ai.Profile(profile_name="oci_ai_profile")
       return {"response": profile.chat(prompt=prompt)}


   @app.get("/show_sql")
   def show_sql(prompt: str):
       profile = select_ai.Profile(profile_name="oci_ai_profile")
       return {"sql": profile.show_sql(prompt=prompt)}

Start the server:

.. code-block:: sh

   uvicorn app:app --host 0.0.0.0 --port 8000

Call the service:

.. code-block:: sh

   curl "http://localhost:8000/chat?prompt=What%20is%20OCI%3F"

Stop the server by pressing ``Ctrl+C`` in the terminal where ``uvicorn`` is
running. FastAPI runs the lifespan shutdown hook and ``select_ai.disconnect()``
closes the pool.

FastAPI asynchronous endpoints
==============================

For async endpoints, initialize the async pool with
``select_ai.create_pool_async()`` and close it with
``select_ai.async_disconnect()``.

.. code-block:: python

   import os
   from contextlib import asynccontextmanager

   from fastapi import FastAPI

   import select_ai

   user = os.getenv("SELECT_AI_USER")
   password = os.getenv("SELECT_AI_PASSWORD")
   dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")


   @asynccontextmanager
   async def lifespan(app: FastAPI):
       select_ai.create_pool_async(
           user=user,
           password=password,
           dsn=dsn,
           min_size=5,
           max_size=10,
           increment=5,
       )
       yield
       await select_ai.async_disconnect()


   app = FastAPI(lifespan=lifespan)


   @app.get("/chat")
   async def chat(prompt: str):
       profile = await select_ai.AsyncProfile(
           profile_name="async_oci_ai_profile"
       )
       return {"response": await profile.chat(prompt=prompt)}

Start and stop the server the same way:

.. code-block:: sh

   uvicorn app:app --host 0.0.0.0 --port 8000

Press ``Ctrl+C`` to stop it.

Pool sizing
===========

Use connection pooling for concurrent services such as API applications,
workloads with mixed fast and slow requests, and applications with tail-latency
requirements. Use standalone connections for simple scripts, command-line
tools, or low-concurrency batch jobs.

Set pool sizing based on expected request concurrency and database capacity.
In multi-worker deployments, each worker process creates its own pool, so total
possible database connections are approximately:

.. code-block:: text

   workers * SELECT_AI_POOL_MAX

Choose pool sizes that leave capacity for other database clients and avoid
overwhelming small database deployments.
