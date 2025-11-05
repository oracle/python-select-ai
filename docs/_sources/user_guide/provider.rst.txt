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

Sync API
++++++++

This method adds ACL allowing database users to invoke AI provider's
HTTP endpoint

.. literalinclude:: ../../../samples/enable_ai_provider.py
   :language: python
   :lines: 14-

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

This method removes ACL blocking database users to invoke AI provider's
HTTP endpoint

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
