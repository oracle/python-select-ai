.. _provider:

An AI Provider in Select AI refers to the service provider of the
LLM, transformer or both for processing and generating responses to natural
language prompts. These providers offer models that can interpret and convert
natural language for the use cases highlighted under the LLM concept.

See `Select your AI Provider <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-about.html#GUID-FDAEF22A-5DDF-4BAE-A465-C1D568C75812>`__
for the supported providers

.. latex:clearpage::

**********************
``Provider``
**********************

.. autoclass:: select_ai.Provider
   :members:

.. latex:clearpage::

*********************************
``AnthropicProvider``
*********************************
.. autoclass:: select_ai.AnthropicProvider
   :members:

.. latex:clearpage::

*****************************
``AzureProvider``
*****************************
.. autoclass:: select_ai.AzureProvider
   :members:

.. latex:clearpage::

*****************************
``AWSProvider``
*****************************
.. autoclass:: select_ai.AWSProvider
   :members:

.. latex:clearpage::

******************************
``CohereProvider``
******************************
.. autoclass:: select_ai.CohereProvider
   :members:

.. latex:clearpage::

*****************************
``OpenAIProvider``
*****************************
.. autoclass:: select_ai.OpenAIProvider
   :members:

.. latex:clearpage::

******************************
``OCIGenAIProvider``
******************************
.. autoclass:: select_ai.OCIGenAIProvider
   :members:

.. latex:clearpage::

******************************
``GoogleProvider``
******************************
.. autoclass:: select_ai.GoogleProvider
   :members:

.. latex:clearpage::

***********************************
``HuggingFaceProvider``
***********************************
.. autoclass:: select_ai.HuggingFaceProvider
   :members:

.. latex:clearpage::

**************************
Enable AI service provider
**************************

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

Sync API
++++++++

This method grants execute privilege on the packages
``DBMS_CLOUD``, ``DBMS_CLOUD_AI`` and ``DBMS_CLOUD_PIPELINE``. It
also enables the database user to invoke the AI(LLM) endpoint

.. literalinclude:: ../../../samples/enable_ai_provider.py
   :language: python
   :lines: 15-

output::

    Enabled AI provider for user: <select_ai_db_user>

.. latex:clearpage::

Async API
+++++++++
.. literalinclude:: ../../../samples/async/enable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Enabled AI provider for user: <select_ai_db_user>

.. latex:clearpage::

***************************
Disable AI service provider
***************************

Sync API
++++++++

.. literalinclude:: ../../../samples/disable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Disabled AI provider for user:  <select_ai_db_user>

.. latex:clearpage::

Async API
+++++++++

.. literalinclude:: ../../../samples/async/disable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Disabled AI provider for user:  <select_ai_db_user>
