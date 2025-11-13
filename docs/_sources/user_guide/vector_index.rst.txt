.. _vector_index:

``VectorIndex`` supports Retrieval Augmented Generation (RAG).
For e.g., you can convert text into vector embeddings and store them in a
vector store. Select AI will augment the natural language prompt by retrieving
content from the vector store using semantic similarity search.

****************************
``VectorIndex`` Object Model
****************************

.. _vectorindexfig:
.. figure:: /image/vector_index.png
   :alt: Select AI Vector Index

.. latex:clearpage::

*************************
``VectorIndexAttributes``
*************************

A ``VectorIndexAttributes`` object can be created with
``select_ai.VectorIndexAttributes()``. Also check
`vector index attributes <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html#GUID-F6A65B2A-AE6D-4751-BDD7-137D49248160>`__


.. autoclass:: select_ai.VectorIndexAttributes
   :members:


``OracleVectorIndexAttributes``
+++++++++++++++++++++++++++++++

.. autoclass:: select_ai.OracleVectorIndexAttributes
   :members:

.. latex:clearpage::

********************
``VectorIndex`` API
********************


A ``VectorIndex`` object can be created with ``select_ai.VectorIndex()``

.. autoclass:: select_ai.VectorIndex
   :members:


Check the examples below to understand how to create vector indexes

.. latex:clearpage::

Create vector index
+++++++++++++++++++

In the following example, vector database provider is Oracle and
objects (to create embedding for) reside in OCI's object store

.. literalinclude:: ../../../samples/vector_index_create.py
   :language: python
   :lines: 14-

output::

    Created vector index: test_vector_index

.. latex:clearpage::

List vector index
+++++++++++++++++

.. literalinclude:: ../../../samples/vector_index_list.py
   :language: python
   :lines: 15-

output::

    Vector index TEST_VECTOR_INDEX
    Vector index profile Profile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=None)

.. latex:clearpage::


Fetch vector index
+++++++++++++++++++++++++++

You can fetch the vector index attributes and associated AI profile using
the class method ``VectorIndex.fetch(index_name)``

.. literalinclude:: ../../../samples/vector_index_fetch.py
   :language: python
   :lines: 14-

output::

    OracleVectorIndexAttributes(chunk_size=1024, chunk_overlap=128, location='https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph', match_limit=5, object_storage_credential_name='my_oci_ai_profile_key', profile_name='oci_vector_ai_profile', refresh_rate=1450, similarity_threshold=0.5, vector_distance_metric='COSINE', vector_db_endpoint=None, vector_db_credential_name=None, vector_db_provider=<VectorDBProvider.ORACLE: 'oracle'>, vector_dimension=None, vector_table_name=None, pipeline_name='TEST_VECTOR_INDEX$VECPIPELINE')

    Profile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_custom_source_uri=None, enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model='cohere.embed-english-v3.0', model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=MY OCI AI Profile)

.. latex:clearpage::

Update vector index attributes
++++++++++++++++++++++++++++++

To update attributes, use either ``vector_index.set_attribute()`` or
``vector_index.set_attributes()``

.. literalinclude:: ../../../samples/vector_index_update_attributes.py
   :language: python
   :lines: 14-

output::

    OracleVectorIndexAttributes(chunk_size=1024, chunk_overlap=128, location='https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph', match_limit=5, object_storage_credential_name='my_oci_ai_profile_key', profile_name='oci_vector_ai_profile', refresh_rate=1450, similarity_threshold=0.5, vector_distance_metric='COSINE', vector_db_endpoint=None, vector_db_credential_name=None, vector_db_provider=<VectorDBProvider.ORACLE: 'oracle'>, vector_dimension=None, vector_table_name=None, pipeline_name='TEST_VECTOR_INDEX$VECPIPELINE')

.. latex:clearpage::

RAG using vector index
++++++++++++++++++++++

.. literalinclude:: ../../../samples/vector_index_rag.py
   :language: python
   :lines: 14-

output::

   The conda environments in your object store are:
    1. fccenv
    2. myrenv
    3. fully-loaded-mlenv
    4. graphenv

    These environments are listed in the provided data as separate JSON documents, each containing information about a specific conda environment.

    Sources:
      - fccenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/fccenv-manifest.json)
      - myrenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/myrenv-manifest.json)
      - fully-loaded-mlenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/fully-loaded-mlenv-manifest.json)
      - graphenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/graphenv-manifest.json)

.. latex:clearpage::

Delete vector index
+++++++++++++++++++

.. literalinclude:: ../../../samples/vector_index_delete.py
   :language: python
   :lines: 12-

output::

    Deleted vector index: test_vector_index

.. latex:clearpage::

************************
``AsyncVectorIndex`` API
************************

A ``AsyncVectorIndex`` object can be created with ``select_ai.AsyncVectorIndex()``

.. autoclass:: select_ai.AsyncVectorIndex
   :members:

.. latex:clearpage::

Async create vector index
+++++++++++++++++++++++++

.. literalinclude:: ../../../samples/async/vector_index_create.py
   :language: python
   :lines: 14-

output::

    created vector index: test_vector_index


.. latex:clearpage::

Async list vector index
++++++++++++++++++++++++

.. literalinclude:: ../../../samples/async/vector_index_list.py
   :language: python
   :lines: 15-

output::

    Vector index TEST_VECTOR_INDEX
    Vector index profile AsyncProfile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=None)


.. latex:clearpage::


Async fetch vector index
+++++++++++++++++++++++++++++++++

You can fetch the vector index attributes and associated AI profile using
the class method ``AsyncVectorIndex.fetch(index_name)``

.. literalinclude:: ../../../samples/async/vector_index_fetch.py
   :language: python
   :lines: 14-

output::

    OracleVectorIndexAttributes(chunk_size=1024, chunk_overlap=128, location='https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph', match_limit=5, object_storage_credential_name='my_oci_ai_profile_key', profile_name='oci_vector_ai_profile', refresh_rate=1450, similarity_threshold=0.5, vector_distance_metric='COSINE', vector_db_endpoint=None, vector_db_credential_name=None, vector_db_provider=<VectorDBProvider.ORACLE: 'oracle'>, vector_dimension=None, vector_table_name=None, pipeline_name='TEST_VECTOR_INDEX$VECPIPELINE')

    AsyncProfile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_custom_source_uri=None, enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model='cohere.embed-english-v3.0', model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=MY OCI AI Profile)

.. latex:clearpage::

Async update vector index attributes
++++++++++++++++++++++++++++++++++++

To update attributes, use either ``async_vector_index.set_attribute()`` or
``async_vector_index.set_attributes()``

.. literalinclude:: ../../../samples/async/vector_index_update_attributes.py
   :language: python
   :lines: 14-

output::

    OracleVectorIndexAttributes(chunk_size=1024, chunk_overlap=128, location='https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph', match_limit=5, object_storage_credential_name='my_oci_ai_profile_key', profile_name='oci_vector_ai_profile', refresh_rate=1450, similarity_threshold=0.5, vector_distance_metric='COSINE', vector_db_endpoint=None, vector_db_credential_name=None, vector_db_provider=<VectorDBProvider.ORACLE: 'oracle'>, vector_dimension=None, vector_table_name=None, pipeline_name='TEST_VECTOR_INDEX$VECPIPELINE')

.. latex:clearpage::

Async RAG using vector index
++++++++++++++++++++++++++++

.. literalinclude:: ../../../samples/async/vector_index_rag.py
   :language: python
   :lines: 15-

output::

    The conda environments in your object store are:
    1. fccenv
    2. myrenv
    3. fully-loaded-mlenv
    4. graphenv

    These environments are listed in the provided data as separate JSON documents, each containing information about a specific conda environment.

    Sources:
      - fccenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/fccenv-manifest.json)
      - myrenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/myrenv-manifest.json)
      - fully-loaded-mlenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/fully-loaded-mlenv-manifest.json)
      - graphenv-manifest.json (https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph/graphenv-manifest.json)
