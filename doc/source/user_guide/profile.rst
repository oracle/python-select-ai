.. _profile:

An AI profile is a specification that includes the AI provider to use and other
details regarding metadata and database objects required for generating
responses to natural language prompts.

An AI profile object can be created using ``select_ai.Profile()``

********************
Profile Object Model
********************

.. _profilefig:
.. figure:: /image/profile_provider.png
   :alt: Select AI Profile and Providers

*******************************
Base ``Profile`` API
*******************************
.. autoclass:: select_ai.BaseProfile
   :members:

*******************************
``Profile`` API
*******************************

.. autoclass:: select_ai.Profile
   :members:

**************************
Create Profile
**************************

.. literalinclude:: ../../../samples/profile_create.py
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

.. literalinclude:: ../../../samples/profile_narrate.py
   :language: python

output::

    Prompt is:  How many promotions are there in the sh database?
    There are 503 promotions in the database.

    Prompt is:  How many products are there in the sh database ?
    There are 72 products in the database.


**************************
Show SQL
**************************

.. literalinclude:: ../../../samples/profile_show_sql.py
   :language: python

output::

    Prompt is:  How many promotions are there in the sh database?
    SELECT COUNT("p"."PROMO_ID") AS "PROMOTION_COUNT" FROM "SH"."PROMOTIONS" "p"

    Prompt is:  How many products are there in the sh database ?
    SELECT COUNT("p"."PROD_ID") AS "NUMBER_OF_PRODUCTS" FROM "SH"."PRODUCTS" "p"

**************************
Run SQL
**************************

.. literalinclude:: ../../../samples/profile_run_sql.py
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

.. literalinclude:: ../../../samples/profile_chat.py
   :language: python

output::

    OCI stands for Oracle Cloud Infrastructure. It is a comprehensive cloud computing platform provided by Oracle Corporation that offers a wide range of services for computing, storage, networking, database, and more.
    ...
    ...
    OCI competes with other major cloud providers, including Amazon Web Services (AWS), Microsoft Azure, Google Cloud Platform (GCP), and IBM Cloud.

**************************
List profiles
**************************

.. literalinclude:: ../../../samples/profiles_list.py
   :language: python

output::

    OCI_AI_PROFILE

*************
Async Profile
*************

async_profile.rst
