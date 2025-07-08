.. _profile:

An AI profile is a specification that includes the AI provider to use and other
details regarding metadata and database objects required for generating
responses to natural language prompts.

An AI profile object can be created using ``select_ai.Profile()``

*******************************
Base ``Profile`` methods
*******************************
.. autoclass:: select_ai.BaseProfile
   :members:

*******************************
Synchronous ``Profile`` methods
*******************************

.. autoclass:: select_ai.Profile
   :members:

**************************
Enable AI service provider
**************************

This method grants execute privilege on the packages
``DBMS_CLOUD``, ``DBMS_CLOUD_AI`` and ``DBMS_CLOUD_PIPELINE``. It
also enables the user to invoke the AI(LLM) endpoint hosted at a
certain domain

.. literalinclude:: ../../../examples/enable_ai_provider.py
   :language: python

output::

    Enabled AI provider for users:  ['SPARK_DB_USER']

**************************
Create credential
**************************

This method creates a credential to authenticate to the AI provider. In this
example, we create a credential object to authenticate to OCI Gen AI service
provider

.. literalinclude:: ../../../examples/create_ai_credential.py
   :language: python

output::

    Created credential:  my_oci_ai_profile_key

**************************
Create Profile
**************************

.. literalinclude:: ../../../examples/profile_create.py
   :language: python

output::

    Created profile  oci_ai_profile
    Profile attributes are:  ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=[{'owner': 'SH'}], object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name=None)
    Profile attributes as Python dict:  {'annotations': None,
     'case_sensitive_values': None,
     'comments': None,
     'constraints': None,
     'conversation': None,
     'credential_name': 'my_oci_ai_profile_key',
     'enable_source_offsets': None,
     'enable_sources': None,
     'enforce_object_list': None,
     'max_tokens': 1024,
     'object_list': [{'owner': 'SH'}],
     'object_list_mode': None,
     'provider': OCIGenAIProvider(embedding_model=None,
                                  model=None,
                                  provider_name='oci',
                                  provider_endpoint=None,
                                  region='us-chicago-1',
                                  oci_apiformat='GENERIC',
                                  oci_compartment_id=None,
                                  oci_endpoint_id=None,
                                  oci_runtimetype=None),
     'seed': None,
     'stop_tokens': None,
     'streaming': None,
     'temperature': None,
     'vector_index_name': None}


**************************
Narrate
**************************

.. literalinclude:: ../../../examples/profile_narrate.py
   :language: python

output::

    Prompt is:  How many promotions are there in the sh database?
    There are 503 promotions in the database.

    Prompt is:  How many products are there in the sh database ?
    There are 72 products in the database.


**************************
Show SQL
**************************

.. literalinclude:: ../../../examples/profile_show_sql.py
   :language: python

output::

    Prompt is:  How many promotions are there in the sh database?
    SELECT COUNT("p"."PROMO_ID") AS "PROMOTION_COUNT" FROM "SH"."PROMOTIONS" "p"

    Prompt is:  How many products are there in the sh database ?
    SELECT COUNT("p"."PROD_ID") AS "NUMBER_OF_PRODUCTS" FROM "SH"."PRODUCTS" "p"

**************************
Run SQL
**************************

.. literalinclude:: ../../../examples/profile_run_sql.py
   :language: python

output::

    Prompt is:  How many promotions are there in the sh database?
    Index(['Number of Promotions'], dtype='object')
       Number of Promotions
    0                   503
    Prompt is:  How many products are there in the sh database ?
    Index(['Number of Products'], dtype='object')
       Number of Products
    0                  72


**************************
Chat
**************************

.. literalinclude:: ../../../examples/profile_chat.py
   :language: python

output::

    OCI stands for Oracle Cloud Infrastructure. It is a comprehensive cloud computing platform provided by Oracle Corporation that offers a wide range of services for computing, storage, networking, database, and more.
    ...
    ...
    OCI competes with other major cloud providers, including Amazon Web Services (AWS), Microsoft Azure, Google Cloud Platform (GCP), and IBM Cloud.

**************************
List profiles
**************************

.. literalinclude:: ../../../examples/profiles_list.py
   :language: python


output::

    Profile(profile_name=OCI_VECTOR_AI_PROFILE, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=MY OCI AI Profile)

    Profile(profile_name=OCI_AI_PROFILE, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=[{'owner': 'SH'}], object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model='meta.llama-3.1-70b-instruct', provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name=None), description=MY OCI AI Profile)

    Profile(profile_name=OCI_GEN_AI_PROFILE, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='COHERE', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name=None), description=MY OCI AI Profile)


***************************
Disable AI service provider
***************************

.. literalinclude:: ../../../examples/disable_ai_provider.py
   :language: python

output::

    Disabled AI provider for user:  ['SPARK_DB_USER']
