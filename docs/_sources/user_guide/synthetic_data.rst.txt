.. _synthetic_data:

Synthetic data generation uses a Select AI profile to populate database tables
with generated rows. It is useful for demos, development, testing, and
prototyping when representative data is needed but production data should not
be copied.

Synthetic data is inserted into the target tables in the connected database
schema or in the schema identified by ``owner_name`` or ``object_list``. Before
running generation, make sure the connected user has privileges on the target
tables and that the Select AI profile is configured with a provider and
credential.

Use synthetic data generation with care in shared schemas. The API writes rows
to the target tables; use dedicated test tables or schemas when experimenting.

Generation modes
================

Use ``object_name`` for a single target table:

.. code-block:: python

   attributes = select_ai.SyntheticDataAttributes(
       object_name="MOVIE",
       record_count=100,
       user_prompt="the release date for the movies should be in 2019",
   )

Use ``object_list`` for multiple target tables in one request:

.. code-block:: python

   attributes = select_ai.SyntheticDataAttributes(
       object_list=[
           {
               "owner": "SH",
               "name": "MOVIE",
               "record_count": 100,
               "user_prompt": (
                   "the release date for the movies should be in 2019"
               ),
           },
           {"owner": "SH", "name": "ACTOR", "record_count": 10},
           {"owner": "SH", "name": "DIRECTOR", "record_count": 5},
       ]
   )

Exactly one of ``object_name`` or ``object_list`` must be set.

Generation parameters
=====================

Use ``SyntheticDataParams`` to control how generation is performed:

.. code-block:: python

   params = select_ai.SyntheticDataParams(
       sample_rows=100,
       table_statistics=True,
       priority="HIGH",
       comments=True,
   )

   attributes = select_ai.SyntheticDataAttributes(
       object_name="MOVIE",
       record_count=100,
       user_prompt="Generate movie data for releases in 2019.",
       params=params,
   )

``sample_rows`` controls how many existing rows are used as examples for the
model. ``table_statistics`` and ``comments`` include additional table metadata.
``priority`` controls resource priority for generation work; supported values
are ``HIGH``, ``MEDIUM``, and ``LOW``.

Sync and async APIs
===================

Use ``Profile.generate_synthetic_data(...)`` for synchronous applications and
``await AsyncProfile.generate_synthetic_data(...)`` for asynchronous
applications:

.. code-block:: python

   profile = select_ai.Profile(profile_name="oci_ai_profile")
   profile.generate_synthetic_data(
       synthetic_data_attributes=attributes,
   )

.. code-block:: python

   async_profile = await select_ai.AsyncProfile(
       profile_name="async_oci_ai_profile",
   )
   await async_profile.generate_synthetic_data(
       synthetic_data_attributes=attributes,
   )

For additional database-side attribute details, see the
`generate_synthetic_data PL/SQL API <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html#GUID-818B6825-FBF4-4EE9-9CE5-D3C6A74462AA>`__.

.. latex:clearpage::

***************************
``SyntheticDataAttributes``
***************************

.. autoclass:: select_ai.SyntheticDataAttributes
   :members:

.. latex:clearpage::

***********************
``SyntheticDataParams``
***********************

.. autoclass:: select_ai.SyntheticDataParams
   :members:

.. latex:clearpage::

****************************
Single table synthetic data
****************************

The below example shows single table synthetic data generation

Single Table Sync API
+++++++++++++++++++++

.. literalinclude:: ../../../samples/profile_gen_single_table_synthetic_data.py
   :language: python
   :lines: 14-

output::

    SQL> select count(*) from movie;

      COUNT(*)
    ----------
           100

.. latex:clearpage::

Single Table Async API
+++++++++++++++++++++

.. literalinclude:: ../../../samples/async/profile_gen_single_table_synthetic_data.py
   :language: python
   :lines: 12-

output::

    SQL> select count(*) from movie;

      COUNT(*)
    ----------
           100

.. latex:clearpage::


****************************
Multi table synthetic data
****************************

The below example shows multi-table synthetic data generation

Multi table Sync API
++++++++++++++++++++

.. literalinclude:: ../../../samples/profile_gen_multi_table_synthetic_data.py
   :language: python
   :lines: 14-


output::

    SQL> select count(*) from actor;

      COUNT(*)
    ----------
        40

    SQL> select count(*) from director;

      COUNT(*)
    ----------
        13

    SQL> select count(*) from movie;

      COUNT(*)
    ----------
           300


Multi table Async API
+++++++++++++++++++++


.. literalinclude:: ../../../samples/async/profile_gen_multi_table_synthetic_data.py
   :language: python
   :lines: 12-


output::

    SQL> select count(*) from actor;

      COUNT(*)
    ----------
        40

    SQL> select count(*) from director;

      COUNT(*)
    ----------
        13

    SQL> select count(*) from movie;

      COUNT(*)
    ----------
           300
