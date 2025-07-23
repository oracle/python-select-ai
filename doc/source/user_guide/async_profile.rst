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

***********************
Async Profile creation
***********************

.. literalinclude:: ../../../samples/async/profile_create.py
   :language: python

output::

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


***********************
Async explain SQL
***********************

.. literalinclude:: ../../../samples/async/profile_explain_sql.py
   :language: python

output::

    To answer the question "How many promotions", we need to write a SQL query that counts the number of rows in the "PROMOTIONS" table. Here is the query:

    ```sql
    SELECT
      COUNT("p"."PROMO_ID") AS "Number of Promotions"
    FROM
      "SH"."PROMOTIONS" "p";
    ```

    Explanation:

    * We use the `COUNT` function to count the number of rows in the table.
    * We use the table alias `"p"` to refer to the `"PROMOTIONS"` table.
    * We enclose the table name and column name in double quotes to make them case-sensitive.
    * We use the `AS` keyword to give an alias to the count column, making it easier to read.

    This query will return the total number of promotions in the `"PROMOTIONS"` table.


***********************
Async run SQL
***********************

.. literalinclude:: ../../../samples/async/profile_run_sql.py
   :language: python

output::

       PROMOTION_COUNT
    0              503

***********************
Async show SQL
***********************

.. literalinclude:: ../../../samples/async/profile_show_sql.py
   :language: python

output::

    SELECT COUNT("p"."PROMO_ID") AS "PROMOTION_COUNT" FROM "SH"."PROMOTIONS" "p"


***********************
Async concurrent SQL
***********************

.. literalinclude:: ../../../samples/async/profile_sql_concurrent_tasks.py
   :language: python

output::

    SELECT COUNT("c"."CUST_ID") AS "customer_count" FROM "SH"."CUSTOMERS" "c"

    To answer the question "How many promotions", we need to write a SQL query that counts the number of rows in the "PROMOTIONS" table. Here is the query:

    ```sql
    SELECT
      COUNT("p"."PROMO_ID") AS "number_of_promotions"
    FROM
      "SH"."PROMOTIONS" "p";
    ```

    Explanation:

    * We use the `COUNT` function to count the number of rows in the table.
    * We use the table alias `"p"` to refer to the `"PROMOTIONS"` table.
    * We specify the schema name `"SH"` to ensure that we are accessing the correct table.
    * We enclose the table name, schema name, and column name in double quotes to make them case-sensitive.
    * The `AS` keyword is used to give an alias to the calculated column, in this case, `"number_of_promotions"`.

    This query will return the total number of promotions in the `"PROMOTIONS"` table.

       PROMOTION_COUNT
    0              503

**********
Async chat
**********

.. literalinclude:: ../../../samples/async/profile_chat.py
   :language: python

output::

    OCI stands for several things depending on the context:

    1. **Oracle Cloud Infrastructure (OCI)**: This is a cloud computing service offered by Oracle Corporation. It provides a range of services including computing, storage, networking, database, and more, allowing businesses to build, deploy, and manage applications and services in a secure and scalable manner.

    ...
    ..
    OML4PY provides a Python interface to OML, allowing users to create, manipulate, and analyze models using Python scripts. It enables users to leverage the power of OML and OMF from within Python, making it easier to integrate modeling and simulation into larger workflows and applications.
    ...
    ...

    An Autonomous Database is a type of database that uses artificial intelligence (AI) and machine learning (ML) to automate many of the tasks typically performed by a database administrator (DBA)
    ...
    ...

*********************
Async pipeline
*********************

.. literalinclude:: ../../../samples/async/profile_pipeline.py
   :language: python

output::

    Result 0 for prompt 'What is Oracle Autonomous Database?' is: Oracle Autonomous Database is a cloud-based database service that uses artificial intelligence (AI) and machine learning (ML) to automate many of the tasks associated with managing a database. It is a self-driving, self-securing, and self-repairing database that eliminates the need for manual database administration, allowing users to focus on higher-level tasks.


    Result 1 for prompt 'Generate SQL to list all customers?' is: SELECT "c"."CUST_ID" AS "Customer ID", "c"."CUST_FIRST_NAME" AS "First Name", "c"."CUST_LAST_NAME" AS "Last Name", "c"."CUST_EMAIL" AS "Email" FROM "SH"."CUSTOMERS" "c"

    Result 2 for prompt 'Explain the query: SELECT * FROM sh.products' is: ```sql
    SELECT
      p.*
    FROM
      "SH"."PRODUCTS" p;
    ```

    **Explanation:**

    This query is designed to retrieve all columns (`*`) from the `"SH"."PRODUCTS"` table.

    Here's a breakdown of the query components:


    Result 3 for prompt 'Explain the query: SELECT * FROM sh.products' is: ORA-20000: Invalid action - INVALID ACTION

****************************
List profiles asynchronously
****************************

.. literalinclude:: ../../../samples/async/profiles_list.py
   :language: python

output::

    OCI_AI_PROFILE
