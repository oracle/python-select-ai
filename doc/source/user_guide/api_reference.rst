.. _error-handling:

************************************
Errors, sessions, and result objects
************************************

Error handling
==============

SDK validation and lookup errors are separate from Oracle driver errors.
Catch a specific SDK exception when the application can recover from it.
Database and provider failures surfaced by PL/SQL can raise
``oracledb.DatabaseError``; inspect the driver error code when deciding what
the application should do. Avoid retrying authorization or configuration
failures without correcting their cause.

.. code-block:: python

   import oracledb
   import select_ai

   # Assumes an open connection. Missing profiles are not created here.
   try:
       profile = select_ai.Profile.fetch("APP_PROFILE")
       answer = profile.chat("Explain retrieval augmented generation.")
   except select_ai.ProfileNotFoundError:
       print("Create APP_PROFILE or choose an existing profile.")
   except select_ai.DatabaseNotConnectedError:
       print("Establish a connection before using the profile.")
   except oracledb.DatabaseError as exc:
       error, = exc.args
       print(f"Database operation failed (code {error.code}).")
       raise

Do not expose raw database errors or connection credentials in public HTTP
responses. For web applications, translate expected failures into your
application's error response and close pools in the application shutdown hook.

.. automodule:: select_ai.errors
   :members:

Session objects
===============

Obtain sessions through ``Profile.chat_session()`` or
``AsyncProfile.chat_session()``. A session holds a connection for the duration
of its context. Consume and close streaming iterators inside that context.

.. autoclass:: select_ai.profile.Session
   :members:

.. autoclass:: select_ai.async_profile.AsyncSession
   :members:

Agent history results
=====================

History APIs yield these typed event objects. Availability and values depend
on the current user's database history views.

.. autoclass:: select_ai.agent.history.TeamHistoryEvent
   :members:

.. autoclass:: select_ai.agent.history.TaskHistoryEvent
   :members:

.. autoclass:: select_ai.agent.history.ToolHistoryEvent
   :members:

Enumerations
============

.. autoclass:: select_ai.action.Action
   :members:

.. autoclass:: select_ai.agent.tool.ToolType
   :members:

.. autoclass:: select_ai.agent.tool.NotificationType
   :members:

.. autoclass:: select_ai.vector_index.VectorDistanceMetric
   :members:

.. autoclass:: select_ai.vector_index.VectorDBProvider
   :members:
