.. _conn:

*****************************
Connecting to Oracle Database
*****************************

``select_ai`` uses the Python thin driver i.e. ``python-oracledb``
to connect to the database and execute PL/SQL subprograms.

.. _sync_conn:

Synchronous connection
======================

To connect to an Oracle Database synchronously, use
``select_ai.connect()`` method as shown below

.. code-block:: python

   import select_ai
   user = "<your_db_user>"
   password = "<your_db_password>"
   dsn = "<your_db_dsn>"
   select_ai.connect(user=user, password=password, dsn=dsn)

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


.. note::

   For m-TLS (wallet) based connection, additional  parameters like
   ``wallet_location``, ``wallet_password``, ``https_proxy``,
   ``https_proxy_port`` can be passed to the ``connect`` and ``async_connect``
   methods
