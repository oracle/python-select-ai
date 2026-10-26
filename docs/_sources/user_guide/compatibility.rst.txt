.. _compatibility:

******************************
Compatibility and requirements
******************************

Select AI for Python 1.5.0 supports Python 3.11, 3.12, 3.13, and 3.14.
Installation requires ``oracledb>=2.0.0`` and ``pandas==3.0.3``. Some optional
features require driver APIs introduced after the minimum installable driver
version; upgrade ``oracledb`` if those APIs are unavailable.

Installing the SDK does not install database PL/SQL packages or enable their
features. Availability depends on the Oracle Database service, version, and
package updates. Consult Oracle's `Select AI and Select AI Agent capability
matrix <https://docs.oracle.com/en/database/oracle/oracle-database/26/saicm/index.html>`__
for your environment before choosing a workflow.

.. list-table:: Feature requirements
   :header-rows: 1
   :widths: 25 35 40

   * - Feature
     - Python installation
     - Database and deployment requirements
   * - Profiles, SQL generation, and chat
     - ``select_ai``
     - ``DBMS_CLOUD_AI`` and ``DBMS_CLOUD``; provider credential and outbound
       database network access. SQL execution also requires object privileges.
   * - Async APIs
     - ``select_ai`` with an async-capable ``oracledb`` driver
     - Thin mode; use an async connection or async pool. Use a pool for
       independent concurrent database operations.
   * - Pipelines
     - ``oracledb>=2.4.0`` with ``create_pipeline()`` and
       ``AsyncConnection.run_pipeline()``
     - True pipelining requires Oracle AI Database 26ai or later. Older
       databases execute individually. See :ref:`pipeline-compatibility`.
   * - RAG vector indexes
     - ``select_ai``
     - Vector-index support in ``DBMS_CLOUD_AI``, ``DBMS_CLOUD_PIPELINE``, an
       embedding model, source access, and database storage capacity.
   * - Agent teams and history
     - ``select_ai``
     - ``DBMS_CLOUD_AI_AGENT`` and the corresponding agent history views.
   * - Profile, index, team, and credential sharing
     - ``select_ai``
     - Database packages providing the relevant grant/revoke APIs. The
       recipient still needs privileges on workflow dependencies.
   * - CLI profile, SQL, and chat commands
     - ``select_ai[cli]``
     - Same requirements as the corresponding SDK operation.
   * - A2A fixed standalone
     - ``select_ai[a2a]``
     - Existing agent team; A2A storage privileges and quota. Supports
       streaming and wallet authentication.
   * - A2A dynamic standalone
     - ``select_ai[a2a]``
     - One Uvicorn process; A2UI-capable client. Polling supported; streaming
       and Oracle wallet authentication are unavailable.
   * - A2A clustered
     - ``select_ai[a2a]`` on gateway and workers
     - Consul and at least one worker. Polling supported; streaming and
       Oracle wallet authentication are unavailable.

The OCI credential-loading examples also require ``oci`` and a configured
OCI API-signing key. This is a sample dependency, rather than an SDK runtime
requirement. See :ref:`Credential <credential>`.

Provider models, regions, and account permissions are independent of Python
package compatibility. Replace example model identifiers and storage URIs
with values supported by your provider account and database integration.
