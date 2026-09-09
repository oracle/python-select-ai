.. _sharing:

**********************
Sharing and ownership
**********************

Select AI objects can be shared with a database user or role. Sharing must be
performed by the object owner, and the grantee must have the package and
database privileges required to use the object.

The sharing APIs are available in both synchronous and asynchronous forms:

.. list-table:: Sharing API summary
   :header-rows: 1
   :widths: 25 37 38
   :align: left

   * - Object
     - Synchronous API
     - Asynchronous API
   * - Profile
     - ``Profile.grant_access()`` and ``revoke_access()``
     - ``AsyncProfile.grant_access()`` and ``revoke_access()``
   * - Vector index
     - ``VectorIndex.grant_access()`` and ``revoke_access()``
     - ``AsyncVectorIndex.grant_access()`` and ``revoke_access()``
   * - Agent team
     - ``Team.grant_access()`` and ``revoke_access()``
     - ``AsyncTeam.grant_access()`` and ``revoke_access()``
   * - Credential
     - ``grant_credential_access()`` and ``revoke_credential_access()``
     - ``async_grant_credential_access()`` and
       ``async_revoke_credential_access()``

Each access method accepts a database user or role name. Access methods return
``None`` after the database grant or revoke operation completes.

Profiles
========

``Profile.fetch()`` and ``Profile.list()`` accept an optional ``owner``
argument. If ``owner`` is omitted, the current schema is used. The fetched
object records its owner in ``profile.owner`` and exposes an owner-qualified
name through ``profile.qualified_name``.

.. code-block:: python

   profile = select_ai.Profile.fetch(
       "OCI_AI_PROFILE",
       owner="APP_OWNER",
   )
   print(profile.owner)
   print(profile.qualified_name)

   profiles = select_ai.Profile.list(
       profile_name_pattern="^OCI_AI_PROFILE$",
       owner="APP_OWNER",
   )
   for profile in profiles:
       print(profile.qualified_name)

Grant and revoke access on the owner-side object:

.. code-block:: python

   profile.grant_access("APP_USER")
   profile.revoke_access("APP_USER")

The asynchronous APIs use the same ``owner`` argument and return an async
iterator from ``AsyncProfile.list()``:

.. code-block:: python

   profile = await select_ai.AsyncProfile.fetch(
       "OCI_AI_PROFILE",
       owner="APP_OWNER",
   )
   profiles = [
       item
       async for item in select_ai.AsyncProfile.list(
           "^OCI_AI_PROFILE$",
           owner="APP_OWNER",
       )
   ]
   print(profile.qualified_name)
   print([item.qualified_name for item in profiles])

   await profile.grant_access("APP_USER")
   await profile.revoke_access("APP_USER")

Vector indexes
==============

``VectorIndex.fetch()`` and ``VectorIndex.list()`` also accept an optional
``owner`` argument. A vector index exposes ``owner`` and the owner-qualified
``qualified_name`` property in the same way as a profile.

.. code-block:: python

   index = select_ai.VectorIndex.fetch(
       "PRODUCT_DOCS",
       owner="APP_OWNER",
   )
   indexes = select_ai.VectorIndex.list(
       index_name_pattern="^PRODUCT_DOCS$",
       owner="APP_OWNER",
   )
   print(index.qualified_name)
   print([item.qualified_name for item in indexes])

   index.grant_access("APP_USER")
   index.revoke_access("APP_USER")

The async form mirrors the synchronous API:

.. code-block:: python

   index = await select_ai.AsyncVectorIndex.fetch(
       "PRODUCT_DOCS",
       owner="APP_OWNER",
   )
   indexes = [
       item
       async for item in select_ai.AsyncVectorIndex.list(
           "^PRODUCT_DOCS$",
           owner="APP_OWNER",
       )
   ]
   await index.grant_access("APP_USER")
   await index.revoke_access("APP_USER")

Agent teams
===========

Agent teams support synchronous and asynchronous access grants and revokes:

.. code-block:: python

   from select_ai.agent import Team

   team = Team.fetch("MOVIE_AGENT_TEAM")
   team.grant_access("APP_USER")
   team.revoke_access("APP_USER")

.. code-block:: python

   from select_ai.agent import AsyncTeam

   team = await AsyncTeam.fetch("MOVIE_AGENT_TEAM")
   await team.grant_access("APP_USER")
   await team.revoke_access("APP_USER")

The current team APIs do not accept an ``owner`` argument. Team fetch and list
operations use the connected user's agent-team views; owner-qualified names
are currently provided for profiles and vector indexes.

Credentials
===========

Credential access is exposed as module-level functions because credentials are
owned in the current schema:

.. code-block:: python

   select_ai.grant_credential_access(
       "MY_PROVIDER_CREDENTIAL",
       "APP_USER",
   )
   select_ai.revoke_credential_access(
       "MY_PROVIDER_CREDENTIAL",
       "APP_USER",
   )

Use the asynchronous equivalents with ``await``:

.. code-block:: python

   await select_ai.async_grant_credential_access(
       "MY_PROVIDER_CREDENTIAL",
       "APP_USER",
   )
   await select_ai.async_revoke_credential_access(
       "MY_PROVIDER_CREDENTIAL",
       "APP_USER",
   )

Credential creation and deletion optionally manage a public synonym with the
same name as the credential. Creating or dropping a public synonym requires the
corresponding ``CREATE PUBLIC SYNONYM`` or ``DROP PUBLIC SYNONYM`` privilege:

.. code-block:: python

   select_ai.create_credential(
       credential=credential,
       replace=True,
       public_synonym=True,
   )
   select_ai.delete_credential(
       "MY_PROVIDER_CREDENTIAL",
       force=True,
       public_synonym=True,
   )

The async functions ``async_create_credential()`` and
``async_delete_credential()`` accept the same ``public_synonym`` option.

Complete sharing sample
========================

The following samples fetch owner-qualified profiles and vector indexes and
exercise grant/revoke operations for profiles, vector indexes, teams, and
credentials. Set ``SELECT_AI_SHARE_GRANTEE`` to a database user or role. The
objects named by the other optional environment variables must already exist,
and the scripts should run as their owner.

.. literalinclude:: ../../../samples/sharing.py
   :language: python
   :lines: 14-

Representative synchronous output is:

output::

    Profile: APP_OWNER.OCI_AI_PROFILE
    Profiles: ['APP_OWNER.OCI_AI_PROFILE']
    Granted profile access to: APP_USER
    Revoked profile access from: APP_USER
    Vector index: APP_OWNER.PRODUCT_DOCS
    Vector indexes: ['APP_OWNER.PRODUCT_DOCS']
    Granted vector index access to: APP_USER
    Revoked vector index access from: APP_USER
    Granted team access to: APP_USER
    Revoked team access from: APP_USER
    Granted credential access to: APP_USER
    Revoked credential access from: APP_USER

The asynchronous sample uses the corresponding async methods:

.. literalinclude:: ../../../samples/async/sharing.py
   :language: python
   :lines: 14-

Representative asynchronous output has the same form:

output::

    Profile: APP_OWNER.ASYNC_OCI_AI_PROFILE
    Profiles: ['APP_OWNER.ASYNC_OCI_AI_PROFILE']
    Granted profile access to: APP_USER
    Revoked profile access from: APP_USER
    Vector index: APP_OWNER.PRODUCT_DOCS
    Vector indexes: ['APP_OWNER.PRODUCT_DOCS']
    Granted vector index access to: APP_USER
    Revoked vector index access from: APP_USER
    Granted team access to: APP_USER
    Revoked team access from: APP_USER
    Granted credential access to: APP_USER
    Revoked credential access from: APP_USER
