.. _privileges:

Admin user should grant execute privilege to select ai database users
on the packages ``DBMS_CLOUD``, ``DBMS_CLOUD_AI``, ``DBMS_CLOUD_AI_AGENT``
and ``DBMS_CLOUD_PIPELINE``

.. note::

   All sample scripts in this documentation read Oracle database connection
   details from the environment. Create a dotenv file ``.env``, export the
   the following environment variables and source it before running the
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

Connect as admin and run the method
``select_ai.grant_privileges(users=select_ai_user)`` to grant relevant select ai
privileges to other users


.. literalinclude:: ../../../samples/select_ai_grant_privilege.py
   :language: python
   :lines: 15-

output::

    Granted privileges to: <select_ai_db_user>

.. latex:clearpage::

***************************
Grant network access
***************************

Connect as admin and run
``select_ai.grant_network_access(...)`` to add a network ACL entry for
host access. This wraps ``DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE`` and can be
used for hosts that require privileges such as ``connect``, ``http``, or
``smtp``.

.. literalinclude:: ../../../samples/grant_network_access.py
   :language: python
   :lines: 14-

output::

    Granted network access to: <select_ai_db_user>

The async API is ``select_ai.async_grant_network_access(...)``.

.. literalinclude:: ../../../samples/async/grant_network_access.py
   :language: python
   :lines: 14-


****************
Revoke privilege
****************

Similarly, to revoke use the method
``select_ai.revoke_privileges(users=select_ai_user)``


.. literalinclude:: ../../../samples/select_ai_revoke_privilege.py
   :language: python
   :lines: 15-

output::

    Granted privileges to: <select_ai_db_user>
