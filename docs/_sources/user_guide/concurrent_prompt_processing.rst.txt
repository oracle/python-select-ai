.. _concurrent_prompt_processing:

****************************
Concurrent prompt processing
****************************

Use concurrent prompt processing when an application needs to send multiple
independent prompts without waiting for each prompt to finish before starting
the next one. The ``select_ai`` module supports this pattern with both the
synchronous ``Profile`` API and the asynchronous ``AsyncProfile`` API.

Create a connection pool before running concurrent work. Use
``select_ai.create_pool()`` for synchronous recipes and
``select_ai.create_pool_async()`` for asynchronous recipes.

Recipe summary
==============

.. list-table::
   :header-rows: 1
   :widths: 18 26 56

   * - Recipe
     - Script
     - When to use
   * - Sync completion
     - :ref:`sync_thread_pool_recipe`
     - Use ``ThreadPoolExecutor`` when prompts are independent and results can
       be handled as soon as each prompt completes.
   * - Sync input order
     - :ref:`sync_ordered_results_recipe`
     - Use ``ThreadPoolExecutor.map()`` when result order must match the input
       prompt order.
   * - Sync queue
     - :ref:`sync_queue_workers_recipe`
     - Use worker threads and a queue for producer-consumer workloads where
       prompts may arrive over time.
   * - Async input order
     - :ref:`async_gather_recipe`
     - Use ``asyncio.gather()`` when result order must match the input prompt
       order.
   * - Async completion
     - :ref:`async_as_completed_recipe`
     - Use ``asyncio.as_completed()`` when each result should be processed as
       soon as it is available.
   * - Async pipeline
     - :ref:`async_pipeline_recipe`
     - Use ``run_pipeline()`` when all prompt/action pairs are known up front
       and should be sent in a single database round trip.
   * - Async queue
     - :ref:`async_queue_workers_recipe`
     - Use async queue workers for long-running async services or background
       prompt processors.

Environment variables
=====================

The recipes use the same connection environment variables as the other samples:

.. code-block:: sh

   export SELECT_AI_USER=<select_ai_db_user>
   export SELECT_AI_PASSWORD=<select_ai_db_password>
   export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>

Optional environment variables control pool sizing and profile names:

.. code-block:: sh

   export SELECT_AI_POOL_MIN=1
   export SELECT_AI_POOL_MAX=4
   export SELECT_AI_POOL_INCREMENT=1
   export SELECT_AI_PROFILE_NAME=oci_ai_profile

Use ``SELECT_AI_PROFILE_NAME=async_oci_ai_profile`` for the async recipes if
that is the async profile name in your environment.

.. _sync_thread_pool_recipe:

``sync_thread_pool.py``
=======================

This recipe uses ``ThreadPoolExecutor`` and ``as_completed()``. Results are
printed in the order they finish.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/sync_thread_pool.py
   :language: python
   :lines: 14-

.. _sync_ordered_results_recipe:

``sync_ordered_results.py``
===========================

This recipe uses ``ThreadPoolExecutor.map()``. Prompts run concurrently, but
results are printed in the same order as the input list.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/sync_ordered_results.py
   :language: python
   :lines: 14-

.. _sync_queue_workers_recipe:

``sync_queue_workers.py``
=========================

This recipe uses worker threads and ``queue.Queue``. It is useful when prompt
producers and prompt processors are separate parts of an application.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/sync_queue_workers.py
   :language: python
   :lines: 14-

.. _async_gather_recipe:

``async_gather.py``
===================

This recipe uses ``asyncio.gather()``. Prompts run concurrently, and results
are returned in the same order as the input task list.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/async_gather.py
   :language: python
   :lines: 14-

.. _async_as_completed_recipe:

``async_as_completed.py``
=========================

This recipe uses ``asyncio.as_completed()``. It is useful for command-line
tools or services that can forward each answer as soon as it is ready.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/async_as_completed.py
   :language: python
   :lines: 14-

.. _async_pipeline_recipe:

``async_pipeline.py``
=====================

This recipe uses ``AsyncProfile.run_pipeline()`` to send multiple
prompt/action pairs in one database round trip. This is different from Python
task concurrency: the application submits a batch and receives the batch
results when the pipeline completes.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/async_pipeline.py
   :language: python
   :lines: 14-

.. _async_queue_workers_recipe:

``async_queue_workers.py``
==========================

This recipe uses ``asyncio.Queue`` and async worker tasks. It is useful for
long-running async applications that receive prompts over time.

.. literalinclude:: ../../../recipes/concurrent_prompt_processing/async_queue_workers.py
   :language: python
   :lines: 14-

Pool sizing
===========

Pool size controls how many database connections the application can use at
one time. For thread and worker recipes, keep the worker count close to the
pool maximum unless the application intentionally needs additional queued work.

In multi-process deployments, each process creates its own pool. Total possible
database connections are approximately:

.. code-block:: text

   processes * SELECT_AI_POOL_MAX

Choose pool sizes that leave capacity for other database clients and for the
AI provider calls made by ``DBMS_CLOUD_AI``.
