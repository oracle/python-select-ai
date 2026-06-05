.. _credential:

A credential object securely stores authentication details from your AI
provider for use by Oracle Database. Select AI profiles, vector indexes, and
agent tools refer to the credential later by ``credential_name``; the secret
values are stored in Oracle Database and are not passed again when the profile
or tool runs.

A credential is created in the connected user's schema by
``DBMS_CLOUD.CREATE_CREDENTIAL``. Create credentials while connected as the
database user that will own and use them. Before creating credentials, make
sure the user has the required Select AI package privileges. If the credential
will be used to call an external AI provider, the database user also needs
network access to that provider endpoint.

Every credential object must include ``credential_name`` and the fields
required by the target provider. The library accepts the following credential
keys: ``credential_name``, ``username``, ``password``, ``user_ocid``,
``tenancy_ocid``, ``private_key``, ``fingerprint``, and ``comments``.

The following table shows AI providers and corresponding credential object
formats.

.. list-table:: AI provider and expected credential format
    :header-rows: 1
    :widths: 30 70
    :align: left

    * - AI provider
      - Credential format
    * - Anthropic
      - .. code-block:: python

            {
                "credential_name": "ANTHROPIC_CRED",
                "username": "anthropic",
                "password": "sk-ant-xxx",
            }
    * - AWS Bedrock
      - .. code-block:: python

            {
                "credential_name": "AWS_BEDROCK_CRED",
                "username": "<aws_access_key_id>",
                "password": "<aws_secret_access_key>",
            }
    * - Azure OpenAI
      - .. code-block:: python

            {
                "credential_name": "AZURE_OPENAI_CRED",
                "username": "azure",
                "password": "<azure_openai_api_key>",
            }
    * - Cohere
      - .. code-block:: python

            {
                "credential_name": "COHERE_CRED",
                "username": "cohere",
                "password": "<cohere_api_key>",
            }
    * - Google
      - .. code-block:: python

            {
                "credential_name": "GOOGLE_CRED",
                "username": "google",
                "password": "<google_api_key>",
            }
    * - HuggingFace
      - .. code-block:: python

            {
                "credential_name": "HUGGINGFACE_CRED",
                "username": "hf",
                "password": "hf_xxx",
            }
    * - OCI Gen AI
      - .. code-block:: python

            {
                "credential_name": "OCI_GENAI_CRED",
                "user_ocid": "<user_ocid>",
                "tenancy_ocid": "<tenancy_ocid>",
                "private_key": "<private_key_contents>",
                "fingerprint": "<fingerprint>",
            }
    * - OpenAI
      - .. code-block:: python

            {
                "credential_name": "OPENAI_CRED",
                "username": "openai",
                "password": "sk-xxx",
            }

.. latex:clearpage::

**************************
Create credential
**************************

In this example, we create a credential object to authenticate to OCI Gen AI
service provider:

Pass ``replace=True`` when you want to recreate an existing credential with the
same name. Without ``replace=True``, creating a credential that already exists
raises a database error.

Sync API
++++++++

.. literalinclude:: ../../../samples/create_ai_credential.py
   :language: python
   :lines: 14-

output::

    Created credential:  my_oci_ai_profile_key

.. latex:clearpage::

Async API
+++++++++

.. literalinclude:: ../../../samples/async/create_ai_credential.py
   :language: python
   :lines: 14-

output::

    Created credential:  my_oci_ai_profile_key

.. latex:clearpage::

**************************
Delete credential
**************************

Use ``select_ai.delete_credential(...)`` to drop a credential that is no longer
needed. Pass ``force=True`` when cleanup should succeed even if the credential
does not exist.

Sync API
++++++++

.. literalinclude:: ../../../samples/delete_ai_credential.py
   :language: python
   :lines: 14-

output::

    Deleted credential: my_oci_ai_profile_key

.. latex:clearpage::

Async API
+++++++++

.. literalinclude:: ../../../samples/async/delete_ai_credential.py
   :language: python
   :lines: 14-

output::

    Deleted credential: my_oci_ai_profile_key
