.. _async_profile:

An AsyncProfile object can be created with ``select_ai.AsyncProfile()``
``AsyncProfile`` support use of concurrent programming with `asyncio <https://docs.python.org/3/library/asyncio.html>`__.
Unless explicitly noted as synchronous, the ``AsyncProfile`` methods should be
used with ``await``.

********************
``AsyncProfile`` API
********************

.. autoclass:: select_ai.AsyncProfile
   :members:

********************
Async SQL generation
********************

.. literalinclude:: ../../../examples/async_examples/1_sql.py
   :language: python

**********
Async chat
**********

.. literalinclude:: ../../../examples/async_examples/2_chat.py
   :language: python

*********************
Async pipeline
*********************

.. literalinclude:: ../../../examples/async_examples/3_pipeline.py
   :language: python

****************************
List profiles asynchronously
****************************

.. literalinclude:: ../../../examples/async_examples/5_list_profiles.py
   :language: python
