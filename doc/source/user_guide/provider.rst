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

Cloud provider profile samples
------------------------------

The repository includes complete profile-creation samples for AWS Bedrock,
Azure OpenAI, and Google Gemini. Each sample:

* grants the Select AI database user HTTP access to the provider endpoint;
* creates or replaces a provider credential; and
* creates or replaces a profile, then sends a test chat request.

Run the samples from the repository root after setting the common database
variables:

* ``SELECT_AI_ADMIN_USER`` and ``SELECT_AI_ADMIN_PASSWORD``;
* ``SELECT_AI_USER`` and ``SELECT_AI_PASSWORD``;
* ``SELECT_AI_DB_CONNECT_STRING``; and
* the provider-specific API key or access-key variables described below.

Do not store production secrets in source files or commit them to the
repository. Adjust the sample region, model, resource, deployment, and object
names for the provider account and database used by your application.

AWS Bedrock
+++++++++++

The `AWS Bedrock profile sample <https://github.com/oracle/python-select-ai/blob/main/samples/profile_create_aws.py>`__
uses ``AWSProvider`` with the following provider settings:

* ``region``: AWS Bedrock region;
* ``model``: text-generation model identifier; and
* ``embedding_model``: embedding model identifier.

Set ``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY`` before running it:

.. code-block:: bash

   python samples/profile_create_aws.py

.. literalinclude:: ../../../samples/profile_create_aws.py
   :language: python
   :lines: 8-

The sample creates ``aws_bedrock_meta_prf`` and prints the saved attributes
and a test response:

output::

    Created profile: aws_bedrock_meta_prf
    {'credential_name': 'AWS_CRED', 'provider': AWSProvider(...), ...}
    Chat response: AWS chat succeeded.

Azure OpenAI
++++++++++++

The `Azure OpenAI profile sample <https://github.com/oracle/python-select-ai/blob/main/samples/profile_create_azure.py>`__
uses ``AzureProvider`` with the following provider settings:

* ``azure_resource_name``: Azure OpenAI resource name;
* ``azure_deployment_name``: text-generation deployment name; and
* ``azure_embedding_deployment_name``: embedding deployment name.

Set ``AZURE_API_KEY`` before running it:

.. code-block:: bash

   python samples/profile_create_azure.py

.. literalinclude:: ../../../samples/profile_create_azure.py
   :language: python
   :lines: 8-

The sample creates ``azureai_prf``, fetches it to verify the saved profile,
and prints a test response:

output::

    Profile(profile_name=azureai_prf, ...)
    Created profile: azureai_prf
    {'credential_name': 'AZUREAI_CRED', 'provider': AzureProvider(...), ...}
    Chat response: Azure chat succeeded.

Google Gemini (GCP)
+++++++++++++++++++

The `Google Gemini profile sample <https://github.com/oracle/python-select-ai/blob/main/samples/profile_create_gcp.py>`__
uses ``GoogleProvider`` with the following provider settings:

* ``model``: Gemini text-generation model identifier; and
* ``embedding_model``: Gemini embedding model identifier.

Set ``GOOGLE_API_KEY`` before running it:

.. code-block:: bash

   python samples/profile_create_gcp.py

.. literalinclude:: ../../../samples/profile_create_gcp.py
   :language: python
   :lines: 8-

The sample creates ``google_gemini_3_6_flash`` and prints the saved attributes
and a test response:

output::

    Created profile: google_gemini_3_6_flash
    {'credential_name': 'GOOGLE_CRED', 'provider': GoogleProvider(...), ...}
    Chat response: GCP chat succeeded.

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
