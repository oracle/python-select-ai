.. _installation:

***************************
Installing ``select_ai``
***************************

.. _installation_requirements:

Installation requirements
==========================

To use ``select_ai`` you need:

- Python 3.9, 3.10, 3.11, 3.12 or 3.13

- ``python-oracledb`` - This package is automatically installed as a dependency requirement

- ``pandas`` - This package is automatically installed as a dependency requirement


.. _quickstart:

``select_ai`` installation
============================

``select_ai`` can be installed from Python's package repository
`PyPI <https://pypi.org/>`__ using
`pip <https://pip.pypa.io/en/latest/installation/>`__.

1. Install `Python 3 <https://www.python.org/downloads>`__ if it is not already
   available. Use any version from Python 3.9 through 3.13.

2. Install ``select_ai``:

  .. code-block:: shell

      python3 -m pip install select_ai --upgrade --user

3. If you are behind a proxy, use the ``--proxy`` option. For example:

  .. code-block:: shell

      python3 -m pip install select_ai --upgrade --user --proxy=http://proxy.example.com:80

4. Create a file ``select_ai_connection_test.py`` such as:

  .. code-block:: python

     import select_ai
     import getpass
     username = ""
     dsn = ""
     password = getpass.getpass(f"Enter password for {username}@{dsn}")
     select_ai.connect(user=user, password=password, dsn=dsn)
     print("Connected to the Database")

5. Run ``select_ai_connection_test.py``

  .. code-block:: shell

     python3 select_ai_connection_test.py

  Enter the database password when prompted and message will be shown:

  .. code-block:: shell

     Connected to the Database



