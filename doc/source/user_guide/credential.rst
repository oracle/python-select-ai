.. _credential:

Credential stores the API key from your AI provider for use by Oracle Database.

**************************
Create credential
**************************

In this example, we create a credential object to authenticate to OCI Gen AI
service provider:

.. literalinclude:: ../../../samples/create_ai_credential.py
   :language: python

output::

    Created credential:  my_oci_ai_profile_key
