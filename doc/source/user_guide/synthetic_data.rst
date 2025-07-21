.. _synthetic_data:

***************************
``SyntheticDataAttributes``
***************************

.. autoclass:: select_ai.SyntheticDataAttributes
   :members:

***********************
``SyntheticDataParams``
***********************

.. autoclass:: select_ai.SyntheticDataParams
   :members:

Also, check the `generate_synthetic_data PL/SQL API <https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/dbms-cloud-ai-package.html#GUID-818B6825-FBF4-4EE9-9CE5-D3C6A74462AA>`__
for attribute details

**************************
Generate synthetic data
**************************

The below example shows single table synthetic data generation

.. literalinclude:: ../../../samples/profile_gen_single_table_synthetic_data.py
   :language: python

output::

    SQL> select count(*) from movie;

      COUNT(*)
    ----------
           100


The below example shows multitable synthetic data generation

.. literalinclude:: ../../../samples/profile_gen_multi_table_synthetic_data.py
   :language: python


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
