.. _profile_attributes:

*************************
``ProfileAttributes``
*************************

This class defines attributes that manage and configure the behavior of an AI
profile. ``ProfileAttributes`` objects are created with
``select_ai.ProfileAttributes()`` and passed to ``select_ai.Profile`` or
``select_ai.AsyncProfile`` when creating or updating a profile.

Profile attributes describe what the profile can access, which AI provider it
uses, how much metadata is sent to the model, and how generation should behave.
Provider-specific settings, such as OCI region or Azure deployment name, are
configured on the provider object and assigned to the ``provider`` attribute.

Common required attributes
==========================

Most profiles need these attributes:

* ``provider``: A ``select_ai.Provider`` object, such as
  ``select_ai.OCIGenAIProvider`` or ``select_ai.OpenAIProvider``.
* ``credential_name``: The database credential used to authenticate with the
  AI provider.
* ``object_list``: The schemas, tables, or views that Select AI can use when
  generating SQL from natural language prompts.

For example:

.. code-block:: python

   attributes = select_ai.ProfileAttributes(
       provider=select_ai.OCIGenAIProvider(
           region="us-chicago-1",
           oci_apiformat="GENERIC",
       ),
       credential_name="my_oci_ai_profile_key",
       object_list=[
           {"owner": "SH", "name": "CUSTOMERS"},
           {"owner": "SH", "name": "SALES"},
       ],
   )

Attribute groups
================

.. list-table:: Profile attribute groups
   :header-rows: 1
   :widths: 30 70
   :align: left

   * - Attribute
     - Purpose
   * - ``provider``
     - Selects the AI provider, model, endpoint, and provider-specific
       options.
   * - ``credential_name``
     - Names the database credential used to authenticate with the AI provider.
   * - ``object_list``
     - Defines which schemas, tables, or views are eligible for natural
       language to SQL generation.
   * - ``object_list_mode``
     - Controls whether Select AI sends metadata for the most relevant objects
       or for all eligible objects.
   * - ``enforce_object_list``
     - Restricts generated SQL to objects in ``object_list``.
   * - ``comments``, ``constraints``, ``annotations``
     - Controls whether additional database metadata is included in the prompt
       sent to the model.
   * - ``case_sensitive_values``
     - Helps prompts that depend on case-sensitive database values.
   * - ``max_tokens``, ``temperature``, ``stop_tokens``, ``seed``
     - Tunes model generation behavior.
   * - ``conversation``
     - Enables conversation history for context-aware chat workflows.
   * - ``vector_index_name``, ``enable_sources``,
       ``enable_source_offsets``, ``enable_custom_source_uri``
     - Configures retrieval-augmented generation and source reporting for
       vector index workflows.

Object list examples
====================

Grant access to every supported object in a schema:

.. code-block:: python

   object_list = [{"owner": "SH"}]

Grant access to selected tables:

.. code-block:: python

   object_list = [
       {"owner": "SH", "name": "CUSTOMERS"},
       {"owner": "SH", "name": "SALES"},
       {"owner": "SH", "name": "PRODUCTS"},
   ]

Restrict generated SQL to the selected objects:

.. code-block:: python

   attributes = select_ai.ProfileAttributes(
       provider=provider,
       credential_name="my_oci_ai_profile_key",
       object_list=[
           {"owner": "SH", "name": "CUSTOMERS"},
           {"owner": "SH", "name": "SALES"},
       ],
       enforce_object_list=True,
   )

Generation controls
===================

Use generation controls when you need more predictable or constrained model
responses:

.. code-block:: python

   attributes = select_ai.ProfileAttributes(
       provider=provider,
       credential_name="my_oci_ai_profile_key",
       object_list=[{"owner": "SH"}],
       max_tokens=1024,
       temperature=0.1,
       stop_tokens='[";"]',
   )

.. autoclass:: select_ai.ProfileAttributes
   :members:
