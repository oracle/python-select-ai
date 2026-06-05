.. _provider:

Provider
========

An AI Provider in Select AI refers to the service provider of the
LLM, transformer or both for processing and generating responses to natural
language prompts. These providers offer models that can interpret and convert
natural language for the use cases highlighted under the LLM concept.

See `Select your AI Provider <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/select-ai-about.html#GUID-FDAEF22A-5DDF-4BAE-A465-C1D568C75812>`__
for the supported providers.

A provider object describes the AI service that a Select AI profile, vector
index, or agent tool should call. The provider object is separate from the
credential object: the provider selects the service, model, endpoint, region,
and provider-specific options, while the credential stores authentication
details.

Most applications should instantiate one of the concrete provider classes
instead of using ``Provider`` directly. Use the base ``Provider`` class when
you need to call a compatible provider endpoint that does not have a dedicated
class in this library.

.. list-table:: Provider classes
   :header-rows: 1
   :widths: 30 35 35
   :align: left

   * - Provider class
     - Provider name
     - Default endpoint behavior
   * - ``AnthropicProvider``
     - ``anthropic``
     - Uses ``api.anthropic.com``.
   * - ``AWSProvider``
     - ``aws``
     - Builds ``bedrock-runtime.<region>.amazonaws.com`` from ``region``.
   * - ``AzureProvider``
     - ``azure``
     - Builds ``<azure_resource_name>.openai.azure.com``.
   * - ``CohereProvider``
     - ``cohere``
     - Uses ``api.cohere.ai``.
   * - ``GoogleProvider``
     - ``google``
     - Uses ``generativelanguage.googleapis.com``.
   * - ``HuggingFaceProvider``
     - ``huggingface``
     - Uses ``api-inference.huggingface.co``.
   * - ``OCIGenAIProvider``
     - ``oci``
     - Uses OCI region and OCI Gen AI attributes.
   * - ``OpenAIProvider``
     - ``openai``
     - Uses ``api.openai.com``.

Examples
--------

OCI Gen AI provider:

.. code-block:: python

   provider = select_ai.OCIGenAIProvider(
       region="us-chicago-1",
       oci_apiformat="GENERIC",
       model="cohere.command-r-plus",
   )

OpenAI provider:

.. code-block:: python

   provider = select_ai.OpenAIProvider(
       model="gpt-4.1",
   )

Azure OpenAI provider:

.. code-block:: python

   provider = select_ai.AzureProvider(
       azure_resource_name="my-azure-openai-resource",
       azure_deployment_name="gpt-4o-deployment",
       azure_embedding_deployment_name="text-embedding-deployment",
   )

AWS Bedrock provider:

.. code-block:: python

   provider = select_ai.AWSProvider(
       region="us-east-1",
       aws_apiformat="ANTHROPIC",
       model="anthropic.claude-3-5-sonnet-20240620-v1:0",
   )

Custom provider endpoint:

.. code-block:: python

   select_ai.create_credential(
       credential={
           "credential_name": "xai_credential",
           "username": "xai",
           "password": "<xai_api_key>",
       },
       replace=True,
   )

   xai_profile = select_ai.Profile(
       profile_name="xai",
       attributes=select_ai.ProfileAttributes(
           provider=select_ai.Provider(
               provider_endpoint="https://api.x.ai",
               model="grok-4-1-fast-reasoning",
           ),
           credential_name="xai_credential",
           object_list=[
               {"owner": "SH", "name": "CUSTOMERS"},
               {"owner": "SH", "name": "SALES"},
               {"owner": "SH", "name": "PRODUCTS"},
               {"owner": "SH", "name": "COUNTRIES"},
           ],
       ),
       replace=True,
   )

   sql = xai_profile.show_sql(
       prompt="How many customers do I have?",
   )

.. latex:clearpage::

``Provider``
------------

.. autoclass:: select_ai.Provider
   :members:

.. latex:clearpage::

``AnthropicProvider``
---------------------
.. autoclass:: select_ai.AnthropicProvider
   :members:

.. latex:clearpage::

``AzureProvider``
-----------------
.. autoclass:: select_ai.AzureProvider
   :members:

.. latex:clearpage::

``AWSProvider``
---------------
.. autoclass:: select_ai.AWSProvider
   :members:

.. latex:clearpage::

``CohereProvider``
------------------
.. autoclass:: select_ai.CohereProvider
   :members:

.. latex:clearpage::

``OpenAIProvider``
------------------
.. autoclass:: select_ai.OpenAIProvider
   :members:

.. latex:clearpage::

``OCIGenAIProvider``
--------------------
.. autoclass:: select_ai.OCIGenAIProvider
   :members:

.. latex:clearpage::

``GoogleProvider``
------------------
.. autoclass:: select_ai.GoogleProvider
   :members:

.. latex:clearpage::

``HuggingFaceProvider``
-----------------------
.. autoclass:: select_ai.HuggingFaceProvider
   :members:

.. latex:clearpage::

Enable AI service provider
--------------------------

Enable using Sync API
+++++++++++++++++++++

This method adds ACL allowing database users to invoke AI provider's
HTTP endpoint. For non-HTTP or port-specific network access, use the network
ACL helpers described in :ref:`Privileges <privileges>`.

.. literalinclude:: ../../../samples/enable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Enabled AI provider for user: <select_ai_db_user>

.. latex:clearpage::

Enable using Async API
++++++++++++++++++++++
.. literalinclude:: ../../../samples/async/enable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Enabled AI provider for user: <select_ai_db_user>

.. latex:clearpage::

Disable AI service provider
---------------------------

This method removes the ACL entry that allows database users to invoke an AI
provider's HTTP endpoint.

Disable using Sync API
++++++++++++++++++++++

.. literalinclude:: ../../../samples/disable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Disabled AI provider for user:  <select_ai_db_user>

.. latex:clearpage::

Disable using Async API
+++++++++++++++++++++++

.. literalinclude:: ../../../samples/async/disable_ai_provider.py
   :language: python
   :lines: 14-

output::

    Disabled AI provider for user:  <select_ai_db_user>
