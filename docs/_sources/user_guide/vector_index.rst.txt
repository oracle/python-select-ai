.. _vector_index:

************
Vector Index
************

``VectorIndex`` supports Retrieval Augmented Generation (RAG). It converts
source documents into vector embeddings, stores the embeddings in a vector
store, and links the vector index to a Select AI profile. When that profile is
used for natural language generation, Select AI can retrieve semantically
similar content from the vector index and use that content as grounding context
for the response.

A vector index is useful when the answer should come from files or documents
that are not represented as relational tables. Typical sources include
documents in Object Storage, product manuals, generated reports, logs, JSON
files, and other text-heavy content that should be searched by meaning rather
than exact keywords.

Before creating a vector index, make sure the database user has:

* A Select AI profile with an AI provider that supports embeddings.
* A credential for the AI provider used by the profile.
* A credential for the object storage location if the source objects are not
  public.
* Network access to the AI provider endpoint and the source location. See
  :ref:`Privileges <privileges>` for network ACL helpers.

The usual lifecycle is:

1. Create a profile with a provider and embedding model.
2. Create ``OracleVectorIndexAttributes`` with the source location and storage
   credential.
3. Create ``VectorIndex`` and call ``create()``.
4. Use the linked profile for RAG actions such as ``narrate()``.
5. Fetch, list, update, disable, enable, or delete the index as needed.

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

For Oracle vector indexes, use ``OracleVectorIndexAttributes``. It sets
``vector_db_provider`` to ``VectorDBProvider.ORACLE`` and is the preferred
attribute class for the examples in this guide.

Common attributes:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Use
   * - ``location``
     - Object Storage URI or source location containing the documents to
       embed.
   * - ``object_storage_credential_name``
     - Credential used to read the source location.
   * - ``profile_name``
     - Select AI profile used to create embeddings and answer RAG prompts.
       If omitted during ``create()``, it is taken from the ``profile`` object
       passed to ``VectorIndex``.
   * - ``chunk_size`` and ``chunk_overlap``
     - Control how source text is split before embedding. Larger chunks keep
       more context together; overlap helps preserve context across chunk
       boundaries.
   * - ``match_limit``
     - Maximum number of matching chunks returned during semantic search.
   * - ``similarity_threshold``
     - Minimum similarity score required for retrieved chunks to be considered
       relevant.
   * - ``vector_distance_metric``
     - Distance metric used to compare embeddings. Supported values include
       ``COSINE``, ``EUCLIDEAN``, ``L2_SQUARED``, ``DOT``, ``MANHATTAN``, and
       ``HAMMING``.
   * - ``refresh_rate``
     - Refresh interval, in minutes, for loading new or changed source data.
   * - ``vector_table_name``
     - Name of the table used to store vector embeddings and chunked data.
       Leave unset unless you need to control the storage table name.
   * - ``enable_sources``
     - Include filenames and source links in RAG output when supported by the
       profile and model response.

Example attributes:

.. code-block:: python

   attributes = select_ai.OracleVectorIndexAttributes(
       location="https://objectstorage.us-ashburn-1.oraclecloud.com/n/example/b/docs/o/product-guides",
       object_storage_credential_name="object_store_credential",
       chunk_size=1024,
       chunk_overlap=128,
       match_limit=5,
       similarity_threshold=0.5,
       vector_distance_metric=select_ai.VectorDistanceMetric.COSINE,
       refresh_rate=1440,
   )

The embedding model is configured on the provider inside the linked
``ProfileAttributes``. Keep the profile provider and vector index attributes
together conceptually: the profile decides how embeddings are generated, while
the vector index attributes decide where content is read from, how it is
chunked, and how the vector store is searched.


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


Use the synchronous API in scripts, notebooks, and command-line tools that use
``select_ai.connect()``. Use ``AsyncVectorIndex`` in applications already using
``asyncio`` and ``select_ai.async_connect()`` or an async connection pool.

Important lifecycle methods:

.. list-table::
   :header-rows: 1

   * - Method
     - Use
   * - ``create(replace=False, wait_for_completion=False)``
     - Create the database vector index and start the load pipeline. If
       ``replace=True`` and the index already exists, the existing index is
       dropped and recreated. Use ``wait_for_completion=True`` when the next
       step depends on the initial load being complete.
   * - ``fetch(index_name)``
     - Build a ``VectorIndex`` proxy from database metadata, including
       attributes and the linked profile when it still exists.
   * - ``list(index_name_pattern=".*")``
     - Iterate over vector indexes visible to the current user. The pattern is
       evaluated with Oracle ``REGEXP_LIKE``.
   * - ``set_attribute()`` and ``set_attributes()``
     - Update one or more index attributes.
   * - ``get_next_refresh_timestamp()``
     - Return the next scheduled refresh timestamp in UTC when the index has a
       refresh rate and a recorded pipeline execution.
   * - ``disable()`` and ``enable()``
     - Pause or resume use of the vector index for loading, indexing,
       searching, and querying.
   * - ``delete(include_data=True, force=False)``
     - Drop the vector index. ``include_data=True`` also removes associated
       vector store data. ``force=True`` ignores missing-index errors.

Check the examples below to understand how to create vector indexes.

.. latex:clearpage::

Create vector index
+++++++++++++++++++

In the following example, vector database provider is Oracle and
objects used to create embeddings reside in OCI Object Storage. The profile
uses an OCI Generative AI provider with an embedding model, and the vector
index is linked to that profile during ``create()``.

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
the class method ``VectorIndex.fetch(index_name)``. Fetch is useful when the
index was created earlier or by another process and you want to inspect or
update it without recreating the original Python object.

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
``vector_index.set_attributes()``. Use ``set_attribute()`` for a single value
and ``set_attributes()`` when updating several values together.

.. literalinclude:: ../../../samples/vector_index_update_attributes.py
   :language: python
   :lines: 14-

output::

    OracleVectorIndexAttributes(chunk_size=1024, chunk_overlap=128, location='https://objectstorage.us-ashburn-1.oraclecloud.com/n/dwcsdev/b/conda-environment/o/tenant1-pdb3/graph', match_limit=5, object_storage_credential_name='my_oci_ai_profile_key', profile_name='oci_vector_ai_profile', refresh_rate=1450, similarity_threshold=0.5, vector_distance_metric='COSINE', vector_db_endpoint=None, vector_db_credential_name=None, vector_db_provider=<VectorDBProvider.ORACLE: 'oracle'>, vector_dimension=None, vector_table_name=None, pipeline_name='TEST_VECTOR_INDEX$VECPIPELINE')

.. latex:clearpage::

RAG using vector index
++++++++++++++++++++++

After ``create()`` succeeds, the profile has its ``vector_index_name`` set to
the new index. Use that profile with text-returning actions such as
``narrate()`` to retrieve relevant chunks from the vector index and ground the
answer in the indexed content.

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

Use ``delete()`` when the index is no longer needed. By default,
``include_data=True`` removes the vector index metadata and the associated
vector store data. Set ``include_data=False`` only when you intentionally want
to keep the underlying vector store data.

.. literalinclude:: ../../../samples/vector_index_delete.py
   :language: python
   :lines: 12-

output::

    Deleted vector index: test_vector_index

.. latex:clearpage::

************************
``AsyncVectorIndex`` API
************************

An ``AsyncVectorIndex`` object can be created with
``select_ai.AsyncVectorIndex()``

.. autoclass:: select_ai.AsyncVectorIndex
   :members:

The async API mirrors the synchronous API. Async profile construction and
vector index methods that access the database must be awaited, and
``AsyncVectorIndex.list()`` is an async iterator.

.. list-table::
   :header-rows: 1

   * - Synchronous API
     - Async API
   * - ``select_ai.connect(...)``
     - ``await select_ai.async_connect(...)``
   * - ``Profile(...)``
     - ``await AsyncProfile(...)``
   * - ``VectorIndex.create(...)``
     - ``await AsyncVectorIndex.create(...)``
   * - ``VectorIndex.fetch(...)``
     - ``await AsyncVectorIndex.fetch(...)``
   * - ``for index in VectorIndex.list(...)``
     - ``async for index in AsyncVectorIndex.list(...)``
   * - ``profile.narrate(...)``
     - ``await async_profile.narrate(...)``

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
