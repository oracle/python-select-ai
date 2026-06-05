.. _privileges:

An admin user should grant execute privilege to Select AI database users
on the packages ``DBMS_CLOUD``, ``DBMS_CLOUD_AI``, ``DBMS_CLOUD_AI_AGENT``,
and ``DBMS_CLOUD_PIPELINE``.

The privilege helper APIs are intended for database administrators who need to
prepare one or more database schemas for Select AI workloads. These operations
should be run from a connection that has permission to grant package execute
privileges and manage database network ACLs.

There are two separate setup steps:

* Package privileges allow a Select AI database user to call the Oracle Database
  PL/SQL packages used by this library.
* Network access allows the database user to make outbound calls to specific
  hosts, such as AI provider endpoints or SMTP servers.

The ``users`` argument accepts either a single database user name or a list of
database user names.

.. note::

   All sample scripts in this documentation read Oracle database connection
   details from the environment. Create a dotenv file ``.env``, export the
   following environment variables and source it before running the
   scripts.

   .. code-block:: sh

       export SELECT_AI_ADMIN_USER=<db_admin>
       export SELECT_AI_ADMIN_PASSWORD=<db_admin_password>
       export SELECT_AI_USER=<select_ai_db_user>
       export SELECT_AI_PASSWORD=<select_ai_db_password>
       export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>
       export TNS_ADMIN=<path/to/dir_containing_tnsnames.ora>

***************
Grant privilege
***************

Connect as an admin user and run
``select_ai.grant_privileges(users=select_ai_user)`` to grant the package
execute privileges required by Select AI. This grants execute access on
``DBMS_CLOUD``, ``DBMS_CLOUD_AI``, ``DBMS_CLOUD_AI_AGENT``, and
``DBMS_CLOUD_PIPELINE``.


.. literalinclude:: ../../../samples/select_ai_grant_privilege.py
   :language: python
   :lines: 15-

output::

    Granted privileges to: <select_ai_db_user>

.. latex:clearpage::

****************
Revoke privilege
****************

Similarly, to revoke use the method
``select_ai.revoke_privileges(users=select_ai_user)``


.. literalinclude:: ../../../samples/select_ai_revoke_privilege.py
   :language: python
   :lines: 15-

output::

    Revoked privileges from: <select_ai_db_user>

.. latex:clearpage::

***************************
Grant network access
***************************

Connect as admin and run
``select_ai.grant_network_access(...)`` to add a network ACL entry for
host access. This wraps ``DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE`` and can be
used for hosts that require privileges such as ``connect``, ``http``, or
``smtp``.

Network ACLs are required when the database needs to reach an external host.
For example, use ``http`` access for AI provider endpoints and ``smtp`` access
for mail servers. Include ``connect`` with protocol-specific privileges when
the host requires it.

When granting access, specify the target host and, when applicable, the port
range. When revoking access, use the same host, privileges, and port range that
were used for the grant.

.. literalinclude:: ../../../samples/grant_network_access.py
   :language: python
   :lines: 14-

output::

    Granted network access to: <select_ai_db_user>

The async API is ``select_ai.async_grant_network_access(...)``.

.. literalinclude:: ../../../samples/async/grant_network_access.py
   :language: python
   :lines: 14-

.. latex:clearpage::

***************************
Revoke network access
***************************

Connect as admin and run
``select_ai.revoke_network_access(...)`` to remove a network ACL entry for
host access. This wraps ``DBMS_NETWORK_ACL_ADMIN.REMOVE_HOST_ACE`` and should
use the same host, privileges, and port range that were used to grant access.

.. literalinclude:: ../../../samples/revoke_network_access.py
   :language: python
   :lines: 14-

output::

    Revoked network access from: <select_ai_db_user>

The async API is ``select_ai.async_revoke_network_access(...)``.

.. literalinclude:: ../../../samples/async/revoke_network_access.py
   :language: python
   :lines: 14-
