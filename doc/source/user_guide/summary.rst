.. _summary:

Summarization uses a Select AI profile to summarize inline text or content
available from a URI. The profile supplies the AI provider, model, credential,
and generation settings. The ``summarize`` APIs are available on both
``Profile`` and ``AsyncProfile``.

Use one content source per call:

* ``content`` for inline text.
* ``location_uri`` for content available from a URL, object storage URI, or
  supported file location.

Use ``credential_name`` when the ``location_uri`` requires a database
credential, such as object storage access. Use ``prompt`` to guide what the
summary should focus on.

Inline content
==============

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")

   summary = profile.summarize(
       content="Long text to summarize...",
       prompt="Summarize the key business implications.",
   )
   print(summary)

Content from a URI
==================

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")

   summary = profile.summarize(
       location_uri="https://en.wikipedia.org/wiki/Astronomy",
   )
   print(summary)

Content from object storage
===========================

Pass ``credential_name`` when the target location requires authentication:

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")

   summary = profile.summarize(
       location_uri=(
           "https://objectstorage.us-ashburn-1.oraclecloud.com/"
           "n/namespace/b/bucket/o/document.txt"
       ),
       credential_name="OBJECT_STORE_CRED",
   )
   print(summary)

Summary parameters
==================

Use ``SummaryParams`` to control output length, output style, chunk processing,
and extractiveness:

.. code-block:: python

   params = select_ai.summary.SummaryParams(
       min_words=50,
       max_words=150,
       summary_style=select_ai.summary.Style.LIST,
       chunk_processing_method=(
           select_ai.summary.ChunkProcessingMethod.MAP_REDUCE
       ),
       extractiveness_level=select_ai.summary.ExtractivenessLevel.MEDIUM,
   )

   summary = profile.summarize(
       content="Long text to summarize...",
       params=params,
   )

Async summary
=============

.. code-block:: python

   async_profile = await select_ai.AsyncProfile(
       profile_name="async_oci_ai_profile",
   )

   summary = await async_profile.summarize(
       content="Long text to summarize...",
       prompt="Summarize the main points.",
   )
   print(summary)

Validation
==========

``summarize`` requires exactly one of ``content`` or ``location_uri``. Passing
both, or passing neither, raises an error.

.. latex:clearpage::

*******************************
SummaryParams
*******************************
.. autoclass:: select_ai.summary.SummaryParams
   :members:

.. latex:clearpage::


*******************************
ChunkProcessingMethod
*******************************
.. autoclass:: select_ai.summary.ChunkProcessingMethod
   :members:

.. latex:clearpage::


*******************************
ExtractivenessLevel
*******************************
.. autoclass:: select_ai.summary.ExtractivenessLevel
   :members:

.. latex:clearpage::


*******************************
SummaryStyle
*******************************
.. autoclass:: select_ai.summary.Style
   :members:

.. latex:clearpage::
