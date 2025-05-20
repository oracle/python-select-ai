.. _introduction:

*****************************************************
Introduction to the Python API for Select AI
*****************************************************

``select_ai`` is a Python module which helps you invoke `DBMS_CLOUD_AI <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html>`__
APIs in a pythonic manner. It lets you manage ``Profiles`` for
AI service providers, generate, run, explain SQL and chat with LLMs.

``select_ai`` supports both synchronous and concurrent(asynchronous)
programming styles

It uses the Python thin driver for Oracle database i.e. ``python-oracledb``
to connect to the database and execute PL/SQL subprograms.

Currently supported Python versions are 3.9, 3.10, 3.11, 3.12 and 3.13.