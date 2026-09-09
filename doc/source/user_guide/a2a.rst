.. _a2a:

********************
Agent2Agent (A2A)
********************

Select AI for Python can expose an Oracle Database AI Agent Team through the
`Agent2Agent (A2A) protocol <https://a2a-protocol.org/>`__. A2A clients can
discover the team from an Agent Card, submit database prompts, and retrieve
task results through the same JSON-RPC endpoint.

There are two deployment modes:

* **Standalone A2A server**: one server owns a configured Oracle connection
  pool and one configured Select AI team. This mode supports streaming and is
  suitable when the service owner controls the database identity.
* **Dynamic A2A gateway**: a public gateway asks the client for a database DSN,
  username, password, and team name through an A2UI form. It opens a temporary
  isolated worker session for that selection. This mode supports task polling,
  but does not advertise or implement streaming.

.. only:: html

   .. figure:: /image/a2a_architecture.svg
      :alt: Architecture comparison of the standalone A2A server and dynamic A2A gateway
      :width: 100%

      Select AI A2A deployment modes. The standalone server fixes the database
      and team at startup; the gateway selects them for each temporary session.

.. only:: latex

   .. figure:: /image/a2a_architecture.png
      :alt: Architecture comparison of the standalone A2A server and dynamic A2A gateway
      :width: 100%

      Select AI A2A deployment modes. The standalone server fixes the database
      and team at startup; the gateway selects them for each temporary session.

CLI-based deployment on any cloud
==================================

The A2A runtimes are provided as ordinary Select AI CLI commands, so they are
not tied to a particular cloud provider. Run the commands on a local machine,
a virtual machine, a container platform, or a Kubernetes service in any cloud
that can reach the required Oracle Database and, for dynamic deployments, the
Consul service:

* ``select-ai a2a serve`` runs the standalone server.
* ``select-ai a2a gateway`` runs the public dynamic gateway.
* ``select-ai a2a worker`` runs a database-bearing dynamic worker.

The commands can be packaged into the platform's preferred container or
process deployment. The Google Cloud scripts documented below are convenience
automation for a Cloud Run/GKE deployment; they are not required to use the
A2A CLI commands on another cloud or on self-managed infrastructure.

The public routes are the same in both modes:

``/.well-known/agent-card.json``
    Agent Card discovery endpoint.

``/a2a/jsonrpc/``
    A2A JSON-RPC endpoint. The endpoint accepts the A2A 1.0 method names and
    the A2A v0.3 compatibility method names.

.. list-table:: Deployment mode comparison
   :header-rows: 1
   :widths: 23 38 39
   :align: left

   * - Concern
     - Standalone server
     - Dynamic gateway
   * - Database and team
     - Fixed in the server configuration.
     - Selected by the client for each session.
   * - Public process
     - ``select-ai a2a serve``
     - ``select-ai a2a gateway``
   * - Session process
     - The server's shared asynchronous connection pool.
     - A worker child process and connection pool per active session.
   * - State
     - Oracle-backed tasks, A2A contexts, and conversations.
     - The same Oracle-backed state, with Consul routing metadata.
   * - Streaming
     - Advertised and supported.
     - Not advertised and rejected; use task polling.
   * - Database authentication
     - DSN/user/password, with optional Oracle wallet.
     - DSN/user/password submitted through A2UI; wallet connections are not
       currently supported by this session path.

Installation and prerequisites
==============================

Install the A2A dependencies before running the server, gateway, or worker:

.. code-block:: bash

   python -m pip install 'select_ai[a2a]'

All modes require:

* an Oracle Database where the Select AI Agent Team is installed;
* a database user with the privileges required by Select AI and the team; and
* network access from the process to Oracle Database.

The standalone server needs one database identity at startup. The gateway does
not need a database identity at startup, but each submitted A2UI connection
form must contain a valid DSN, username, password, and team name.

Protocol compatibility
======================

The server and gateway use the same JSON-RPC URL for A2A 1.0 and v0.3. The
protocol adapter translates the v0.3 method names and Agent Card shape for
clients that have not migrated to A2A 1.0.

.. list-table:: Common A2A operations
   :header-rows: 1
   :widths: 28 34 38
   :align: left

   * - Operation
     - A2A 1.0
     - A2A v0.3 compatibility name
   * - Send a message
     - ``SendMessage``
     - ``message/send``
   * - Stream a message
     - ``SendStreamingMessage``
     - ``message/stream``
   * - Get a task
     - ``GetTask``
     - ``tasks/get``
   * - List tasks
     - ``ListTasks``
     - ``tasks/list``
   * - Cancel a task
     - ``CancelTask``
     - ``tasks/cancel``

For A2A 1.0 clients, use ``A2A-Version: 1.0`` when the client library requires
an explicit version header. A v0.3 client uses the compatibility names. The
``select-ai a2a agent-card`` command prints a v0.3 Agent Card that can be
registered with Gemini Enterprise.

Standalone A2A server
=====================

The standalone server exposes one database AI Agent Team. The database user,
password, DSN, and optional wallet are configured when the process starts. The
team name is required:

.. code-block:: bash

   export SELECT_AI_USER=select_ai_user
   export SELECT_AI_PASSWORD='database-password'
   export SELECT_AI_DB_CONNECT_STRING='db2025adb_medium'

   select-ai a2a serve \
       --team ORACLE_AI_DATABASE_AGENT \
       --host 0.0.0.0 \
       --port 8000 \
       --public-url https://a2a.example.com

The connection values can also be passed with ``--user``, ``--password``, and
``--dsn``. If no password is supplied, the CLI prompts for it. ``--public-url``
is the externally reachable base URL placed into the Agent Card; set it when a
proxy or load balancer sits in front of the process.

The server prints the discovery URL when it starts:

.. code-block:: text

   A2A Agent Card: https://a2a.example.com/.well-known/agent-card.json
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

The exact Uvicorn startup lines vary by version and configuration.

Agent Card discovery
~~~~~~~~~~~~~~~~~~~~

Fetch the card after starting the server:

.. code-block:: bash

   curl -sS https://a2a.example.com/.well-known/agent-card.json | jq

The discovery response is the A2A v0.3-compatible representation used by
clients such as Gemini Enterprise. It identifies the JSON-RPC endpoint and
advertises streaming. The server's internal A2A 1.0 card declares both a
JSON-RPC 1.0 interface and a JSON-RPC v0.3 interface at that same endpoint.

When a service has a public URL, the portable v0.3 card can also be printed
without starting the server:

.. code-block:: bash

   select-ai a2a agent-card \
       --team ORACLE_AI_DATABASE_AGENT \
       --public-url https://a2a.example.com

This command prints JSON similar to:

.. code-block:: json

   {
     "protocolVersion": "0.3",
     "name": "ORACLE_AI_DATABASE_AGENT",
     "url": "https://a2a.example.com/a2a/jsonrpc/",
     "capabilities": {"streaming": true},
     "defaultInputModes": ["text/plain"],
     "defaultOutputModes": ["text/plain"]
   }

The package version, description, and skill list are also included in the
actual output.

Tasks, polling, streaming, and cancellation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The standalone server supports these execution patterns:

* **Blocking**: send a message without a non-blocking option. The request
  waits until the task reaches a terminal state and returns the completed
  task.
* **Non-blocking and polling**: send a v0.3 request with
  ``configuration.blocking: false`` or an A2A 1.0 request with
  ``configuration.returnImmediately: true``. Poll ``tasks/get`` or
  ``GetTask`` until the task reaches ``completed``, ``failed``, ``canceled``,
  or ``rejected``.
* **Streaming**: use ``message/stream`` or ``SendStreamingMessage``. The Agent
  Card advertises ``streaming: true`` and the endpoint returns the protocol's
  streaming events over the HTTP streaming response.
* **Cancellation**: call ``tasks/cancel`` or ``CancelTask`` with the task ID.
  The server updates the task through the A2A task handler and returns its
  canceled state when cancellation succeeds.

The repository includes the
`blocking_task.py sample <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/blocking_task.py>`__
and the
`task_poll.py sample <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/task_poll.py>`__:

.. literalinclude:: ../../../samples/a2a/blocking_task.py
   :language: python
   :lines: 8-

The blocking sample omits ``configuration``. Representative output is:

.. code-block:: text

   Task 7e1...: completed
   {
     "id": "7e1...",
     "status": {"state": "completed", "timestamp": "..."},
     "artifacts": [{"name": "database-agent-result", "parts": ["..."]}]
   }

The task ID, timestamp, and database answer vary for each run.

.. literalinclude:: ../../../samples/a2a/task_poll.py
   :language: python
   :lines: 8-

The polling sample sends a non-blocking request and then calls ``tasks/get``:

.. code-block:: text

   Task 42b...: submitted
   Task 42b...: working
   Task 42b...: completed
   {
     "id": "42b...",
     "status": {"state": "completed", "timestamp": "..."},
     "artifacts": [{"name": "database-agent-result", "parts": ["..."]}]
   }

.. _persistent-oracle-backed-state:

Persistent Oracle-backed state
==============================

Both A2A deployment modes use Oracle implementations of the A2A task and
context stores. In standalone mode, the server initializes these stores when
the application starts. In dynamic gateway mode, ``select-ai a2a gateway``
does not connect to Oracle itself; the ``select-ai a2a worker`` command starts
the internal worker, and each connected worker session initializes the stores
after it opens its supplied database connection. On first initialization, the
stores create these tables if they do not already exist:

``SELECT_AI_A2A_TASKS``
   Stores the task ID, context ID, serialized task JSON, owner, and update
   timestamp. It supports task retrieval, filtering, listing, pagination, and
   deletion.

``SELECT_AI_A2A_CONTEXTS``
   Maps an A2A context and owner to an Oracle conversation ID.

When a request starts a new context, Select AI creates an
``AsyncConversation`` and passes its ID to ``AsyncTeam.run``. Later messages in
the same A2A context reuse that conversation, so the team can use the
conversation history. In standalone mode, task and context ownership is
resolved from the A2A request context; an absent owner is stored as
``anonymous``. In gateway mode, the worker scopes the rows to the temporary
session ID, which is the A2A context ID used to route requests back to that
worker session.

The tables hold task and context metadata, while the conversation prompts and
responses remain in the regular Select AI conversation storage. This means a
server or worker process restart does not discard task records, context
mappings, or conversation history, provided the same database and owner scope
are used. Gateway routing records and worker child processes are temporary:
after a worker session expires or is lost, submit the connection form again so
the gateway can recreate the session and route requests to the durable Oracle
state. The gateway's temporary connection-form task itself is not stored in
Oracle; durable A2A tasks are created by the worker after the database session
is ready.

Wallet-based database connections
=================================

Wallet-based connections apply to the standalone ``select-ai a2a serve``
path. The standalone server passes wallet settings to the Select AI
asynchronous connection pool. Use the unzipped wallet directory with
``SELECT_AI_WALLET_LOCATION`` or ``--wallet-location`` and provide the wallet
password with ``SELECT_AI_WALLET_PASSWORD`` or ``--wallet-password``:

.. code-block:: bash

   export SELECT_AI_WALLET_LOCATION=/secure/wallet/Wallet_database
   export SELECT_AI_WALLET_PASSWORD='wallet-password'
   export SELECT_AI_DB_CONNECT_STRING=db2025adb_medium

   select-ai a2a serve \
       --team ORACLE_AI_DATABASE_AGENT \
       --user SELECT_AI_USER \
       --dsn db2025adb_medium

``--wallet-location`` is used as both the wallet location and the Oracle
configuration directory. Keep wallet files and passwords outside the source
tree. The
`standalone deployment script <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/deploy.sh>`__
can upload a wallet archive
to Secret Manager and expand it into ephemeral Cloud Run storage; see
`Standalone Google Cloud deployment`_ below.

Dynamic A2A gateway
===================

The dynamic mode separates the public A2A protocol endpoint from the
database-bearing runtime. The gateway starts without database credentials. A
worker registers with Consul and waits for the gateway to assign sessions. The
worker's connected sessions use the persistent Oracle-backed task, context, and
conversation state described in :ref:`Persistent Oracle-backed state
<persistent-oracle-backed-state>`; Consul stores only the temporary routing
metadata.

Consul provides the gateway's service-discovery and lightweight routing
control plane. Workers register their address and health check with Consul;
the gateway asks Consul for a passing worker when a session is opened. The
gateway then stores the session-to-worker and task-to-session routes in Consul
so later requests go directly to the worker that owns the session. Consul does
not store database credentials, task payloads, or conversation history.

For local development, install the Consul command-line binary before starting
the local agent. HashiCorp provides package-manager and precompiled-binary
instructions in the `Consul installation guide
<https://developer.hashicorp.com/consul/docs/fundamentals/install>`__.
After installation, verify that the binary is on ``PATH``:

.. code-block:: bash

   consul version

The ``-dev`` agent below is intentionally for local development only. It uses
an in-memory, single-node Consul server bound to loopback. For the Google
Cloud deployment, do not install or run a local agent: the deployment creates
Consul in GKE from the
`Consul manifest <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/gke/consul.yaml>`__.

Start the three local components in separate terminals:

.. code-block:: bash

   # Terminal 1: Consul
   consul agent -dev -bind=127.0.0.1 -client=127.0.0.1

   # Terminal 2: worker
   CONSUL_HTTP_URL=http://127.0.0.1:8500 \
   WORKER_ID=local-worker \
   WORKER_ADDRESS=127.0.0.1 \
   WORKER_PORT=8081 \
   select-ai a2a worker \
       --host 127.0.0.1 \
       --port 8081

   # Terminal 3: public gateway
   select-ai a2a gateway \
       --host 127.0.0.1 \
       --port 8000 \
       --agent-url http://127.0.0.1:8000 \
       --consul-url http://127.0.0.1:8500

The worker uses ``CONSUL_HTTP_URL`` (default ``http://consul:8500``),
``WORKER_ID``, ``WORKER_ADDRESS``, ``WORKER_PORT``, and the optional
``WORKER_ENDPOINT`` environment variables when registering with Consul. The
gateway uses ``AGENT_URL``, ``CONSUL_HTTP_URL``, ``WORKER_SERVICE`` (default
``select-ai-worker``), and ``SESSION_TTL_SECONDS``. The command-line options
override the corresponding environment variables.

The worker must be able to resolve the submitted DSN. For a TNS alias, set
``TNS_ADMIN`` in the worker terminal before starting it. The gateway session
path accepts a DSN, username, and password; it does not currently accept an
Oracle wallet.

The gateway's Agent Card advertises ``streaming: false``. It supports blocking
tasks, non-blocking tasks, task retrieval/listing, and cancellation by
forwarding the request to the worker session. Streaming and push-notification
operations are rejected because the gateway does not proxy a live stream.

A2UI database-connection form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first ``message/send`` for a context returns a temporary task containing a
database connection form. The form is an A2UI v0.9 data artifact with the
``application/json+a2ui`` MIME type. It contains these fields:

.. list-table:: Dynamic connection form
   :header-rows: 1
   :widths: 25 75
   :align: left

   * - Field
     - Purpose
   * - ``dsn``
     - Oracle connect descriptor, simplified connect string, or TNS alias
       available to the worker.
   * - ``username``
     - Database user for this session.
   * - ``password``
     - Database password. The form renders this field as obscured input.
   * - ``team_name``
     - Select AI Agent Team to run in this session.
   * - ``submit_database_connection``
     - A2UI action that submits the four values to the gateway.

After the action is submitted, the gateway selects a healthy worker through
Consul and opens a session. The worker starts a child process, calls
``select_ai.async_connect`` with the supplied DSN/user/password, validates the
team, initializes the Oracle task and context stores, and returns a
``database-session`` artifact. The client can then send ordinary database
prompts with the same A2A context ID.

Credentials are used to open the session and are not written to Consul. Consul
stores only the worker endpoint and expiration for the session, plus task-to-
session routing metadata. The credentials remain in the worker child process
for the lifetime of that session, so use TLS for client-to-gateway traffic and
follow the security policies for any client that renders the form.

The gateway samples perform this handshake automatically. They use the
repository-local helper module
`samples/a2a/gateway/_common.py <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/gateway/_common.py>`__;
``_common``
is not a package that users install with ``pip``. Running the samples from the
repository root as shown below makes that helper available automatically.

The helper functions are:

``call(method, params)``
   Sends one A2A v0.3 JSON-RPC request to the configured gateway endpoint.

``connect(prompt)``
   Sends the initial prompt, reads the A2UI connection form, submits the
   ``SELECT_AI_DB_CONNECT_STRING``, ``SELECT_AI_USER``,
   ``SELECT_AI_PASSWORD``, and ``SELECT_AI_A2A_TEAM`` values, and returns the
   A2A context ID for the connected session.

``send_prompt(prompt, context_id, blocking=None)``
   Sends a database prompt in an existing gateway context. Passing
   ``blocking=False`` adds the non-blocking request option.

``print_task_summary(task)``
   Prints the task state, result artifact name, and text parts without dumping
   the connection-form details.

If you copy a gateway sample into another directory, copy the
`_common.py helper <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/gateway/_common.py>`__
with it, or replace these helpers with an A2A client implementation of your
own.

The complete gateway setup is also documented in the
`gateway sample README <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/gateway/README.md>`__.
The examples below are the
`blocking_task.py sample <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/gateway/blocking_task.py>`__
and the
`task_poll.py sample <https://github.com/oracle/python-select-ai/blob/main/samples/a2a/gateway/task_poll.py>`__.

.. literalinclude:: ../../../samples/a2a/gateway/blocking_task.py
   :language: python
   :lines: 8-

Set the database values before running the sample:

.. code-block:: bash

   export SELECT_AI_DB_CONNECT_STRING='database-dsn'
   export SELECT_AI_USER='database-user'
   export SELECT_AI_PASSWORD='database-password'
   export SELECT_AI_A2A_TEAM='ORACLE_AI_DATABASE_AGENT'

Run it with:

.. code-block:: bash

   python samples/a2a/gateway/blocking_task.py

Representative output is:

.. code-block:: text

   Task 15c...: completed
   Artifact: database-agent-result
   The database contains ...

The gateway polling sample uses the same connection-form handshake, then
passes ``configuration.blocking: false`` and polls ``tasks/get``:

.. literalinclude:: ../../../samples/a2a/gateway/task_poll.py
   :language: python
   :lines: 8-

.. code-block:: text

   Task 91a...: submitted
   Task 91a...: working
   Task 91a...: completed
   Artifact: database-agent-result
   The database contains ...

Session isolation, routing, and cleanup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each successful connection action creates one worker session identified by the
A2A context ID. The worker owns an operating-system child process for that
session. The child process owns its Select AI asynchronous connection, A2A
handler, task store, context store, and database conversation access. Requests
for different sessions therefore do not share database credentials or a
connection pool.

The default session lifetime is 900 seconds (15 minutes). Change it with
``--session-ttl-seconds`` on the worker and gateway, or with the gateway's
``SESSION_TTL_SECONDS`` environment variable. The worker reaper checks for
expired or dead child processes and terminates them. The gateway also checks
the expiry stored in Consul. When a route or child session is no longer
available, the gateway returns an A2UI connection form so the client can
reconnect rather than silently sending a request to a different database.

Consul is used for two kinds of routing metadata:

* the worker service registration and health TTL, which let the gateway select
  a passing worker; and
* ``select-ai/sessions/`` and ``select-ai/tasks/`` key-value records, which
  route a context or task back to the worker that owns it.

The task and conversation contents are not stored in Consul. They are stored
in Oracle by the selected worker. A worker registers a health check and sends
heartbeats; it deregisters on shutdown. The gateway selects healthy workers
round-robin when opening new sessions.

Gateway-to-worker mTLS
~~~~~~~~~~~~~~~~~~~~~~

Local development uses ordinary HTTP. For an internal deployment, the gateway
can authenticate workers and workers can require a gateway client certificate.
All three gateway files are required together:

.. code-block:: bash

   select-ai a2a gateway \
       --agent-url https://gateway.example.com \
       --worker-tls-ca-file /run/secrets/worker-ca.pem \
       --worker-tls-cert-file /run/secrets/gateway-client.crt \
       --worker-tls-key-file /run/secrets/gateway-client.key

Start the worker with the matching server certificate, key, and CA:

.. code-block:: bash

   select-ai a2a worker \
       --tls-cert-file /run/secrets/worker.crt \
       --tls-key-file /run/secrets/worker.key \
       --tls-ca-file /run/secrets/gateway-client-ca.pem

The worker must register an HTTPS endpoint through ``WORKER_ENDPOINT`` when
mTLS is enabled. The gateway verifies the worker certificate with the CA and
presents its client certificate. This mTLS option protects only the
gateway-to-worker HTTP hop. It does not add wallet-based mTLS to the gateway's
database connection path.

Google Cloud deployment
=======================

The repository contains complete deployment workflows under the
`gcloud directory <https://github.com/oracle/python-select-ai/tree/main/gcloud>`__.
The
two scripts deploy different topologies, so choose the directory that matches
the desired runtime model.

Standalone Google Cloud deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`gcloud/standalone/deploy.sh <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/deploy.sh>`__
deploys one private Cloud Run service for one
database and team:

.. code-block:: bash

   gcloud/standalone/deploy.sh \
       --project PROJECT_ID \
       --a2a-team ORACLE_AI_DATABASE_AGENT \
       --build

The script creates or reuses an Artifact Registry repository, runtime service
account, Secret Manager secrets, and Cloud Run service. On the first run it
prompts for the database user, password, and connect descriptor. It injects
them into the service as ``SELECT_AI_USER``, ``SELECT_AI_PASSWORD``, and
``SELECT_AI_DB_CONNECT_STRING``. The service is private; the script grants
``run.routes.invoke`` to the active deployment identity and the Gemini
Enterprise Discovery Engine service agent.

Use ``--build`` when the current checkout should become a new container image.
The script submits
`gcloud/standalone/cloudbuild.yaml <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/cloudbuild.yaml>`__
to Cloud Build, which
builds ``docker/Dockerfile`` from the repository root and pushes the image to
Artifact Registry. Without ``--build``, a later invocation reuses the image
already deployed and only updates Cloud Run configuration or secrets.

Important standalone options include:

* ``--service``: Cloud Run service name; use a different service for each
  fixed team/database deployment.
* ``--a2a-team``: team installed in Oracle Database.
* ``--pool-max-size``: maximum Oracle connections per Cloud Run instance.
* ``--max-instances``: Cloud Run instance limit.
* ``--wallet-archive``: upload or replace an Autonomous Database wallet ZIP.
* ``--rotate-db-credentials``: prompt for and rotate the database secrets.

For a wallet deployment, ``--wallet-archive`` stores the ZIP and wallet
password in service-specific Secret Manager secrets. Cloud Run mounts the ZIP
read-only; the launcher expands it into ephemeral ``/tmp`` storage, verifies
the wallet, and sets ``SELECT_AI_WALLET_LOCATION`` before starting the A2A
server. Do not commit wallet files or put them in the container image.

The standalone script prints the deployed Agent Card JSON at the end. The
service is ready for a client when the printed card points to the final Cloud
Run URL and the client can invoke the private service.

Dynamic gateway Google Cloud deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`gcloud/gateway/deploy.sh <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/deploy.sh>`__
deploys the gateway topology: Cloud Run for the
public gateway, GKE Autopilot for worker replicas, and Consul for discovery and
routing.

.. code-block:: bash

   gcloud/gateway/deploy.sh \
       --project PROJECT_ID \
       --region us-central1 \
       --worker-replicas 3

The script and
`gcloud/gateway/cloudbuild.yaml <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/cloudbuild.yaml>`__
perform these steps:

1. Enable the required Google Cloud APIs and create or reuse Artifact Registry
   and a GKE Autopilot cluster.
2. Configure additive VPC DNS so StatefulSet worker names resolve to current
   Pod IPs after a worker is recreated.
3. Deploy the gateway namespace, internal Consul service, and worker service.
4. Build and publish the image with Cloud Build.
5. Deploy the requested worker replicas with ``select-ai a2a worker`` and the
   selected session TTL.
6. Deploy Cloud Run with ``select-ai a2a gateway`` and set ``AGENT_URL`` to the
   final Cloud Run URL.

The Cloud Run gateway uses direct VPC egress to reach the internal Consul
load-balancer address and worker endpoints. The GKE worker service is headless
service discovery, not a public load balancer. Consul selects a healthy worker
when a session opens; the route is then pinned to that worker.

Important gateway options include:

* ``--cluster`` and ``--gke-dns-domain``: GKE Autopilot cluster and immutable
  additive DNS domain.
* ``--network`` and ``--subnet``: VPC path used by Cloud Run to reach the
  internal worker infrastructure.
* ``--worker-replicas``: number of worker runtimes available for new sessions.
* ``--session-ttl-seconds``: lifetime of temporary database sessions.
* ``--enable-worker-mtls``: create and use gateway-to-worker certificates.
* ``--rotate-worker-mtls``: replace the existing test certificates and restart
  the worker workload.

The default gateway deployment uses private-VPC HTTP between Cloud Run and
GKE. With ``--enable-worker-mtls``, the script creates short-lived test PKI
material in Secret Manager, creates the Kubernetes TLS secrets, deploys the
worker StatefulSet variant, and mounts the gateway client certificate into
Cloud Run. The worker certificate uses the GKE StatefulSet DNS name, so the
``--gke-dns-domain`` value must remain consistent with the cluster.

The gateway deployment does not upload an Oracle wallet because the dynamic
worker session path currently accepts only DSN/user/password. If database mTLS
is required, use the standalone deployment or provide a separate database
connection mechanism to the worker implementation.

The deployment files are intended to be read together:

.. list-table:: Google Cloud A2A deployment files
   :header-rows: 1
   :widths: 32 68
   :align: left

   * - File
     - Role
   * - `gcloud/standalone/deploy.sh <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/deploy.sh>`__
     - Creates and updates one private Cloud Run standalone server.
   * - `gcloud/standalone/cloudbuild.yaml <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/cloudbuild.yaml>`__
     - Builds and publishes the standalone container image.
   * - `gcloud/standalone/README.md <https://github.com/oracle/python-select-ai/blob/main/gcloud/standalone/README.md>`__
     - Documents IAM, secrets, wallet archives, and update behavior.
   * - `gcloud/gateway/deploy.sh <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/deploy.sh>`__
     - Creates or reuses the gateway GKE/Cloud Run topology and supplies build
       substitutions.
   * - `gcloud/gateway/cloudbuild.yaml <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/cloudbuild.yaml>`__
     - Builds the image, deploys Consul and workers, and deploys Cloud Run.
   * - `gcloud/gateway/gke manifests <https://github.com/oracle/python-select-ai/tree/main/gcloud/gateway/gke>`__
     - Namespace, Consul, headless worker service, and HTTP or mTLS worker
       workloads.
   * - `gcloud/gateway/README.md <https://github.com/oracle/python-select-ai/blob/main/gcloud/gateway/README.md>`__
     - Explains the topology, DNS, mTLS test mode, and operational details.

Troubleshooting and security notes
==================================

* If the Agent Card advertises the wrong URL, set ``--public-url`` for the
  standalone server or ``AGENT_URL`` for the gateway. The URL must be the
  client-visible base URL, not an internal container address.
* If the gateway returns the connection form repeatedly, check that the worker
  is passing in Consul, that the worker can resolve and connect to Oracle, and
  that the session TTL has not expired.
* If a task can no longer be retrieved after a worker restart, submit the A2UI
  form again. Consul routes are intentionally tied to the worker session, even
  though task data is durable in Oracle.
* Do not put database passwords in source files, container images, Consul KV,
  or deployment logs. Use Secret Manager for fixed standalone credentials and
  protect the A2UI/gateway path with HTTPS.
* Gateway mTLS and Oracle wallet mTLS are different controls. Gateway mTLS
  authenticates the internal HTTP peer; an Oracle wallet authenticates the
  database connection and is currently available only to the standalone
  server path.

See :ref:`Command Line Interface <cli>` for the common CLI connection options
and :ref:`Connection <conn>` for Select AI database connection setup.
