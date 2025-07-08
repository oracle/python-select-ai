.. _vector_index:

********************
``VectorIndex``
********************

A ``VectorIndex`` object can be created with ``select_ai.VectorIndex()``

.. autoclass:: select_ai.VectorIndex
   :members:

********************
``AsyncVectorIndex``
********************

A ``AsyncVectorIndex`` object can be created with ``select_ai.AsyncVectorIndex()``

.. autoclass:: select_ai.AsyncVectorIndex
   :members:

*************************
``VectorIndexAttributes``
*************************

A ``VectorIndexAttributes`` object can be created with
``select_ai.VectorIndexAttributes()``. Also check
`vector index attributes <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html#GUID-F6A65B2A-AE6D-4751-BDD7-137D49248160>`__


.. autoclass:: select_ai.VectorIndexAttributes
   :members:


*******************************
``OracleVectorIndexAttributes``
*******************************

.. autoclass:: select_ai.OracleVectorIndexAttributes
   :members:


*******************************
``ChromaVectorIndexAttributes``
*******************************

.. autoclass:: select_ai.ChromaVectorIndexAttributes
   :members:


*********************************
``PineconeVectorIndexAttributes``
*********************************

.. autoclass:: select_ai.PineconeVectorIndexAttributes
   :members:


*********************************
``QdrantVectorIndexAttributes``
*********************************

.. autoclass:: select_ai.QdrantVectorIndexAttributes
   :members:

Check the examples below to understand how to create vector indexes

**************************
Vector Index
**************************

In the following example, vector database provider is Oracle and
objects (to create embedding for) reside in OCI's object store

.. literalinclude:: ../../../examples/vector_index_create.py
   :language: python

output::

    created vector index: test_vector_index


.. literalinclude:: ../../../examples/vector_index_list.py
   :language: python

output::

    Vector index TEST_VECTOR_INDEX
    Vector index profile Profile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=None)



*************************************
Asynchronous support for Vector Index
*************************************

.. literalinclude:: ../../../examples/async_examples/vector_index_create.py
   :language: python

output::

    created vector index: test_vector_index


.. literalinclude:: ../../../examples/async_examples/vector_index_list.py
   :language: python

output::

    Vector index TEST_VECTOR_INDEX
    Vector index profile AsyncProfile(profile_name=oci_vector_ai_profile, attributes=ProfileAttributes(annotations=None, case_sensitive_values=None, comments=None, constraints=None, conversation=None, credential_name='my_oci_ai_profile_key', enable_sources=None, enable_source_offsets=None, enforce_object_list=None, max_tokens=1024, object_list=None, object_list_mode=None, provider=OCIGenAIProvider(embedding_model=None, model=None, provider_name='oci', provider_endpoint=None, region='us-chicago-1', oci_apiformat='GENERIC', oci_compartment_id=None, oci_endpoint_id=None, oci_runtimetype=None), seed=None, stop_tokens=None, streaming=None, temperature=None, vector_index_name='test_vector_index'), description=None)
