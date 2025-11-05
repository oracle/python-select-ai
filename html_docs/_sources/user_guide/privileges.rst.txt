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
