.. _installation:

***************************
Installing ``select_ai``
***************************

.. _installation_requirements:

Installation requirements
==========================

To use ``select_ai`` you need:

- Python 3.11, 3.12, 3.13, or 3.14.

- Access to an Oracle Database environment where Select AI is available.

- A database user with the required Select AI package privileges. See
  :ref:`Privileges <privileges>`.

- Network access from the database to any AI provider endpoints you plan to
  use.

- ``python-oracledb`` and ``pandas``. These packages are installed
  automatically as dependencies.

Using a virtual environment is recommended so the package and its dependencies
are isolated from your system Python installation.


.. _quickstart:

``select_ai`` installation
============================

``select_ai`` can be installed from the Python Package Index
`PyPI <https://pypi.org/>`__ using
`pip <https://pip.pypa.io/en/latest/installation/>`__.

1. Install `Python 3 <https://www.python.org/downloads>`__ if it is not already
   available. Use any version from Python 3.11 through 3.14.

2. Create and activate a virtual environment:

   .. code-block:: shell

      python3 -m venv .venv
      source .venv/bin/activate

   On Windows PowerShell:

   .. code-block:: powershell

      py -3 -m venv .venv
      .venv\Scripts\Activate.ps1

3. Upgrade ``pip``:

   .. code-block:: shell

      python -m pip install --upgrade pip

4. Install ``select_ai``:

   .. code-block:: shell

      python -m pip install --upgrade select_ai

5. If you want the optional command line interface, install the ``cli`` extra:

   .. code-block:: shell

      python -m pip install --upgrade "select_ai[cli]"

   This installs the ``select-ai`` command. See :ref:`Command Line Interface
   <cli>`.

6. If you are behind a proxy, use the ``--proxy`` option. For example:

   .. code-block:: shell

      python -m pip install --upgrade select_ai --proxy=http://proxy.example.com:80


Connection smoke test
=====================

After installation, verify that Python can import ``select_ai`` and connect to
Oracle Database.

1. Set database connection environment variables:

   .. code-block:: shell

      export SELECT_AI_USER=<select_ai_db_user>
      export SELECT_AI_PASSWORD=<select_ai_db_password>
      export SELECT_AI_DB_CONNECT_STRING=<db_connect_string>

2. Create a file ``select_ai_connection_test.py``:

   .. code-block:: python

      import os

      import select_ai

      user = os.getenv("SELECT_AI_USER")
      password = os.getenv("SELECT_AI_PASSWORD")
      dsn = os.getenv("SELECT_AI_DB_CONNECT_STRING")

      select_ai.connect(user=user, password=password, dsn=dsn)
      print("Connected to the Database")

3. Run the script:

   .. code-block:: shell

      python select_ai_connection_test.py

   If the connection succeeds, the script prints:

   .. code-block:: shell

      Connected to the Database

Install documentation dependencies
==================================

If you are building this documentation locally from the repository, install the
documentation dependencies:

.. code-block:: shell

   python -m pip install -r doc/requirements.txt

Then build the docs with the project's Sphinx command or Makefile target.

.. latex:clearpage::
