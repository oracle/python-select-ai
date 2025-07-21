.. _provider:

An AI Provider in Select AI refers to the service provider of the
LLM, transformer or both for processing and generating responses to natural
language prompts. These providers offer models that can interpret and convert
natural language for the use cases highlighted under the LLM concept.

See `Select your AI Provider <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-about.html#GUID-FDAEF22A-5DDF-4BAE-A465-C1D568C75812>`__
for the supported providers

**********************
``Provider``
**********************

.. autoclass:: select_ai.Provider
   :members:

*********************************
``AnthropicProvider``
*********************************
.. autoclass:: select_ai.AnthropicProvider
   :members:

*****************************
``AzureProvider``
*****************************
.. autoclass:: select_ai.AzureProvider
   :members:

*****************************
``AWSProvider``
*****************************
.. autoclass:: select_ai.AWSProvider
   :members:

******************************
``CohereProvider``
******************************
.. autoclass:: select_ai.CohereProvider
   :members:

*****************************
``OpenAIProvider``
*****************************
.. autoclass:: select_ai.OpenAIProvider
   :members:


******************************
``OCIGenAIProvider``
******************************
.. autoclass:: select_ai.OCIGenAIProvider
   :members:


******************************
``GoogleProvider``
******************************
.. autoclass:: select_ai.GoogleProvider
   :members:

***********************************
``HuggingFaceProvider``
***********************************
.. autoclass:: select_ai.HuggingFaceProvider
   :members:

**************************
Enable AI service provider
**************************

This method grants execute privilege on the packages
``DBMS_CLOUD``, ``DBMS_CLOUD_AI`` and ``DBMS_CLOUD_PIPELINE``. It
also enables the user to invoke the AI(LLM) endpoint hosted at a
certain domain

.. literalinclude:: ../../../samples/enable_ai_provider.py
   :language: python

output::

    Enabled AI provider for users:  ['SPARK_DB_USER']

***************************
Disable AI service provider
***************************

.. literalinclude:: ../../../samples/disable_ai_provider.py
   :language: python

output::

    Disabled AI provider for user:  ['SPARK_DB_USER']
