.. _sharing:

**********************
Sharing and ownership
**********************

Share a saved profile, vector index, agent team, or credential with a database
user or role. Run grants and revokes while connected as the object owner. The
recipient also needs the database and package :ref:`Privileges <privileges>`
required to use that object.

The examples below use owner ``APP_OWNER`` and recipient ``APP_USER``. Replace
these names with your schemas. Each example assumes that its named object
already exists. Sharing an object does not grant access to other database
objects or services used by the workflow.

Connect before running an example
=================================

For synchronous examples, connect as the object owner:

.. code-block:: python

   import os
   import select_ai

   select_ai.connect(
       user=os.environ["SELECT_AI_USER"],       # APP_OWNER
       password=os.environ["SELECT_AI_PASSWORD"],
       dsn=os.environ["SELECT_AI_DB_CONNECT_STRING"],
   )

Call ``select_ai.disconnect()`` when finished. For asynchronous examples, use
``await select_ai.async_connect(...)`` with the same arguments inside an async
function, and call ``await select_ai.async_disconnect()`` when finished.
The async snippets below belong inside that function.

.. latex:clearpage::

Profiles
========

Grant access to an existing profile while connected as ``APP_OWNER``:

.. code-block:: python

   profile = select_ai.Profile.fetch("OCI_AI_PROFILE")
   profile.grant_access("APP_USER")

In a separate connection as ``APP_USER``, fetch the shared profile by its name
and owner. The ``qualified_name`` property identifies both:

.. code-block:: python

   profile = select_ai.Profile.fetch("OCI_AI_PROFILE", owner="APP_OWNER")
   print(profile.qualified_name)
   print(profile.chat(prompt="What is retrieval augmented generation?"))

The qualified name printed is ``APP_OWNER.OCI_AI_PROFILE``. The chat answer
depends on the configured provider. To withdraw access, reconnect as
``APP_OWNER`` and run:

.. code-block:: python

   profile = select_ai.Profile.fetch("OCI_AI_PROFILE")
   profile.revoke_access("APP_USER")

The async sequence uses ``AsyncProfile``. Run each step in the indicated
user's connection:

.. code-block:: python

   # As APP_OWNER: share the profile.
   profile = await select_ai.AsyncProfile.fetch("OCI_AI_PROFILE")
   await profile.grant_access("APP_USER")

   # In a separate connection as APP_USER: use the shared profile.
   shared = await select_ai.AsyncProfile.fetch(
       "OCI_AI_PROFILE", owner="APP_OWNER"
   )
   print(shared.qualified_name)
   print(await shared.chat(prompt="What is retrieval augmented generation?"))

   # Reconnect as APP_OWNER when access should end.
   await profile.revoke_access("APP_USER")

``Profile.list()`` and ``AsyncProfile.list()`` also accept ``owner``. If it is
omitted, they list the current schema. See
:ref:`List profiles <user_guide/profile:List profiles>` and
:ref:`List profiles asynchronously <user_guide/async_profile:List profiles asynchronously>`
for connection setup, filtering, and reuse.

.. latex:clearpage::

Vector indexes
==============

Share an existing vector index while connected as ``APP_OWNER``:

.. code-block:: python

   index = select_ai.VectorIndex.fetch("PRODUCT_DOCS")
   index.grant_access("APP_USER")

In a separate connection as ``APP_USER``, address the index by its owner:

.. code-block:: python

   index = select_ai.VectorIndex.fetch("PRODUCT_DOCS", owner="APP_OWNER")
   print(index.qualified_name)  # APP_OWNER.PRODUCT_DOCS

Reconnect as ``APP_OWNER`` to withdraw access:

.. code-block:: python

   index = select_ai.VectorIndex.fetch("PRODUCT_DOCS")
   index.revoke_access("APP_USER")

Use ``AsyncVectorIndex`` for the same sequence in an async application:

.. code-block:: python

   # As APP_OWNER.
   index = await select_ai.AsyncVectorIndex.fetch("PRODUCT_DOCS")
   await index.grant_access("APP_USER")

   # In a separate connection as APP_USER.
   shared = await select_ai.AsyncVectorIndex.fetch(
       "PRODUCT_DOCS", owner="APP_OWNER"
   )
   print(shared.qualified_name)

   # Reconnect as APP_OWNER when access should end.
   await index.revoke_access("APP_USER")

``VectorIndex.list(owner="APP_OWNER")`` lists visible indexes in that schema;
``AsyncVectorIndex.list(owner="APP_OWNER")`` returns an async iterator.
See :ref:`Vector Index <vector_index>` for creating and using an index for RAG.

.. latex:clearpage::

Agent teams
===========

While connected as the team owner, grant access to an existing team:

.. code-block:: python

   from select_ai.agent import Team

   team = Team.fetch("MOVIE_AGENT_TEAM")
   team.grant_access("APP_USER")

When the recipient no longer needs access, run this as the team owner:

.. code-block:: python

   team.revoke_access("APP_USER")

For async applications, use ``AsyncTeam`` and await each operation:

.. code-block:: python

   from select_ai.agent import AsyncTeam

   team = await AsyncTeam.fetch("MOVIE_AGENT_TEAM")
   await team.grant_access("APP_USER")

   # Revoke later, while connected as the team owner.
   await team.revoke_access("APP_USER")

Team fetch and list operations use the connected user's agent-team views and
do not accept an ``owner`` argument. See :ref:`AI Agent <agent>` for team
creation and execution.

.. latex:clearpage::

Credentials
===========

Credentials use module-level access functions. While connected as the
credential owner, share an existing provider credential:

.. code-block:: python

   select_ai.grant_credential_access("MY_PROVIDER_CREDENTIAL", "APP_USER")

Revoke access when the recipient no longer needs it:

.. code-block:: python

   select_ai.revoke_credential_access("MY_PROVIDER_CREDENTIAL", "APP_USER")

The async functions take the same arguments:

.. code-block:: python

   await select_ai.async_grant_credential_access(
       "MY_PROVIDER_CREDENTIAL", "APP_USER"
   )

   # Revoke later, while connected as the credential owner.
   await select_ai.async_revoke_credential_access(
       "MY_PROVIDER_CREDENTIAL", "APP_USER"
   )

Access functions return ``None`` after the grant or revoke completes. They do
not print a confirmation message.

Credential creation and deletion can also manage a public synonym with the
same name. Pass ``public_synonym=True`` to ``create_credential()`` or
``delete_credential()`` (or their async equivalents). Creating or dropping the
synonym requires ``CREATE PUBLIC SYNONYM`` or ``DROP PUBLIC SYNONYM``
respectively. See :ref:`Credential <credential>` for credential setup.

Runnable sharing scripts
=========================

The repository also provides a
`synchronous sharing script <https://github.com/oracle/python-select-ai/blob/main/samples/sharing.py>`__
and an
`asynchronous sharing script <https://github.com/oracle/python-select-ai/blob/main/samples/async/sharing.py>`__
that exercise all four object types. Use these when you want to check the APIs
together after working through the individual examples above.

Set the common database connection variables and ``SELECT_AI_SHARE_GRANTEE``.
The connected user must own all four objects. The scripts use these defaults;
override them if your objects have other names:

.. list-table:: Sharing script configuration
   :header-rows: 1
   :widths: 48 52

   * - Environment variable
     - Default
   * - ``SELECT_AI_PROFILE_NAME``
     - ``oci_ai_profile`` (sync); ``async_oci_ai_profile`` (async)
   * - ``SELECT_AI_VECTOR_INDEX_NAME``
     - ``test_vector_index``
   * - ``SELECT_AI_TEAM_NAME``
     - ``MOVIE_AGENT_TEAM``
   * - ``SELECT_AI_CREDENTIAL_NAME``
     - ``my_oci_ai_profile_key``
   * - ``SELECT_AI_OWNER``
     - Current schema; if set, use the connected owner's schema.

Run either script from the repository root:

.. code-block:: bash

   export SELECT_AI_SHARE_GRANTEE=APP_USER
   python samples/sharing.py
   # Or run the async version:
   python samples/async/sharing.py

Each script prints the owner-qualified profile and vector-index names, then
confirms each grant and revoke. The scripts revoke every grant they make;
use the individual examples above to leave an object shared for application use.
