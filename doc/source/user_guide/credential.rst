.. _credential:

Credential object securely stores API key from your AI provider for use by Oracle Database.
The following table shows AI Provider and corresponding credential object format

.. list-table:: AI Provider and expected credential format
    :header-rows: 1
    :widths: 30 70
    :align: left

    * - AI Provider
      - Credential format
    * - Anthropic
      - .. code-block:: python

            {"username": "anthropic", "password": "sk-xxx"}
    * - HuggingFace
      -  .. code-block:: python

            {"username": "hf", "password": "hf_xxx"}
    * - OCI Gen AI
      - .. code-block:: python

           {"user_ocid": "", "tenancy_ocid": "", "private_key": "", "fingerprint": ""}
    * - OpenAI
      - .. code-block:: python

           {"username": "openai", "password": "sk-xxx"}




.. latex:clearpage::

**************************
Create credential
**************************

In this example, we create a credential object to authenticate to OCI Gen AI
service provider:

.. literalinclude:: ../../../samples/create_ai_credential.py
   :language: python

output::

    Created credential:  my_oci_ai_profile_key
