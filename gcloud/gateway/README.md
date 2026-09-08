# Dynamic gateway

Dynamic gateway mode exposes one public A2A endpoint. Each user dynamically
selects an Oracle database connection and Select AI team through the A2UI
connection form. A session remains available for 15 minutes by default. Set a
different lifetime in seconds with `--session-ttl-seconds`; for example,
`--session-ttl-seconds 1800` keeps sessions for 30 minutes.

## Protocol architecture

```text
┌──────────────┐  A2A JSON-RPC/HTTP  ┌──────────────────┐                                     ┌────────────────────────────┐
│ A2A client   │────────────────────►│ Gateway instances│──── route lookup/update ──────────► │ Service Registry           │
└──────────────┘                     │ Public A2A API   │                                     │ Service discovery          │
                                     │ A2UI bootstrap   │                                     │ Session routes             │
                                     └────────┬─────────┘                                     │ Task routes                │
                                              │ Internal protobuf                             │                            │
                                              ▼                                               │                            │
                                     ┌──────────────────┐                                     │                            │
                                     │ Worker pool      │──── registration / heartbeat------->│                            │
                                     │ worker-0, ...    │                                     │                            │
                                     └────────┬─────────┘                                     └────────────────────────────┘
                                              │ one child per database session
                                              ▼
                                     ┌──────────────────┐
                                     │ Session runtime  │
                                     │ A2A handler      │
                                     │ Task/context     │
                                     │ stores           │
                                     │ Database session │
                                     └────────┬─────────┘
                                              │ SQL / Select AI
                                              ▼
                                     ┌──────────────────┐
                                     │ Oracle Database  │
                                     └──────────────────┘
```

The gateway is the only public A2A application. It selects a worker through
the Service Registry, opens a session there, and proxies subsequent A2A calls
using the internal protobuf protocol. The selected worker starts one child
runtime for that session. The child owns the database connection,
`DefaultRequestHandler`, `OracleTaskStore`, and `OracleContextStore`.

The session connection path currently accepts a DSN, username, and password.
Oracle Database wallet-based mTLS is not yet supported for these dynamic
sessions. The optional worker mTLS mode below protects the gateway-to-worker
HTTP connection; it does not provide database mTLS.

The Service Registry stores only service-discovery and non-secret
session/task-to-worker metadata. Task payloads and context mappings remain in
Oracle. Connection-form tasks are response-only bootstrap tasks: they are
created by the gateway before a database session exists and are not persisted
or routed.

## GCP deployment

The protocol architecture above is implemented on GCP as follows:

```text
 ┌──────────────────────┐
 │ A2A / Gemini client  │
 └──────────┬───────────┘
            │ public A2A
            v
 ┌────────────────────────────┐
 │ Cloud Run gateway          │
 │ A2A proxy + form bootstrap │
 └──────┬───────────┬─────────┘
        │       │ private VPC: mTLS request to worker hostname
        │       │
        │       │     ┌─────────────────────── GKE ───────────────────────┐
        │       └────>│ [Headless Service + managed VPC DNS]              │
        │             │ worker hostname → current worker Pod IP           │
        │             │                    │                              │
        │             │                    v                              │
        │             │ [StatefulSet worker-0 / worker-1 / ...]           │
        │             │ session child: A2A handler + Oracle stores        │
        │             │                    │                              │
        │             │                    v                              │
        │             │              Oracle Database                      │
        │             │                                                   │
        │             │ [Consul]                                          │
        └────────────>│ selects healthy worker; returns worker hostname   │
                      └───────────────────────────────────────────────────┘
```

Run this from the repository root:

```bash
gcloud/gateway/deploy.sh --project PROJECT_ID
```

The script creates the Artifact Registry repository and GKE Autopilot cluster
when they do not already exist. The cluster is created with
GKE additive VPC DNS: GKE owns the worker DNS records and keeps them current
when a worker Pod is recreated. Cloud Build then:

1. builds the existing `docker/Dockerfile` image once;
2. deploys the GKE namespace and internal Consul service;
3. deploys the requested number of GKE worker replicas using
   `select-ai a2a worker`;
4. deploys the same image to Cloud Run using `select-ai a2a gateway`;
5. sets the final Cloud Run URL in `AGENT_URL` for the Agent Card.

Common options:

```bash
gcloud/gateway/deploy.sh \
  --project PROJECT_ID \
  --region us-central1 \
  --cluster select-ai-a2a-gateway \
  --gke-dns-domain select-ai-a2a-gateway.internal \
  --worker-replicas 3 \
  --network default \
  --subnet default
```

The Cloud Run gateway uses direct VPC egress to reach the internal Consul load
balancer and GKE worker pod addresses. The gateway keeps only the connection
form task transiently, before a database session exists. Connected task and
context state is stored in Oracle on the selected worker. Workers, rather
than the gateway, provide the clustered capacity for dynamic sessions.
The deployment currently keeps one gateway instance as an operational default;
the gateway does not cache forms or connected task/context state. Gateway
scaling does not change session affinity because Consul stores the session and
task routes.

`cloudbuild.yaml` is the complete build and deployment workflow. It supplies
the generated image and Consul endpoint values to the Cloud Run gateway at
deployment time.

## Optional worker mTLS test mode

Local testing does not use mTLS. The default GCloud deployment also keeps the
current private-VPC HTTP worker transport.

This mTLS mode applies only between the Cloud Run gateway and GKE workers. It
is independent of Oracle Database authentication, and does not enable wallet-
based database mTLS for gateway sessions.

For a short-lived GCloud mTLS test:

```bash
gcloud/gateway/deploy.sh \
  --project PROJECT_ID \
  --enable-worker-mtls \
  --mtls-cert-validity-days 365
```

This mode is intentionally self-contained and is not a production PKI design.
The deployment script generates an ephemeral CA and leaf certificates valid for
365 days by default, then removes the CA private key from its restricted
temporary directory. It never prints or stores that key. The leaf material is
first stored in Google Secret Manager. Cloud Build then creates the Kubernetes
Secrets used by the workers.

Set `--mtls-cert-validity-days DAYS` to choose the lifetime for both leaf
certificates: the gateway client certificate and the worker server certificate.
The CA is issued for one additional day.

The first mTLS deployment creates these certificates. Later mTLS deployments
reuse them, including when changing `--worker-replicas`. To deliberately
replace the CA and both leaf certificates, add `--rotate-worker-mtls`. Rotation
recreates the worker StatefulSet and ends active worker sessions.

Workers run as a StatefulSet. The `select-ai-worker` headless Service gives
each worker a stable name, for example
`select-ai-worker-0.select-ai-worker.select-ai-gateway.svc.select-ai-a2a-gateway.internal`.
Consul registers that name, so the gateway reaches the exact worker that owns a
session. GKE Cloud DNS updates its Pod-IP record automatically after a worker
is recreated. There is no worker load balancer, custom Cloud DNS zone, or
deployment-time Pod-IP snapshot.

`--gke-dns-domain` must be unique in the VPC and cannot end in `.local`. It is
immutable after cluster creation. Autopilot supports additive VPC DNS only when
the cluster is created, so an older cluster without it cannot be reused by this
deployment. Use a new `--cluster` name for the first migration, verify it, then
delete the old cluster when you are ready.

If existing mTLS material was issued for a different GKE DNS domain, the script
replaces it automatically before deploying the replacement cluster.

### How a worker DNS name is decided

GKE gives a StatefulSet Pod a DNS name using this form:

```text
<pod>.<headless-service>.<namespace>.svc.<gke-dns-domain>
```

For this deployment, worker 0 is:

```text
select-ai-worker-0.select-ai-worker.select-ai-gateway.svc.select-ai-a2a-gateway.internal
```

`select-ai-worker-0` is the StatefulSet Pod name, `select-ai-worker` is the
headless Service, `select-ai-gateway` is the Kubernetes namespace, and
`select-ai-a2a-gateway.internal` is the `--gke-dns-domain` value. GKE updates
the resulting record when the Pod IP changes.

### Certificate mounts

Worker certificate files are mounted from Kubernetes Secrets:

| Container file | Kubernetes Secret | Secret key | Used for |
| --- | --- | --- | --- |
| `/var/run/select-ai-mtls/tls.crt` | `select-ai-worker-server-tls` | `tls.crt` | worker HTTPS server certificate |
| `/var/run/select-ai-mtls/tls.key` | `select-ai-worker-server-tls` | `tls.key` | worker HTTPS private key |
| `/var/run/select-ai-mtls/gateway-ca.crt` | `select-ai-gateway-client-ca` | `ca.crt` | validates the gateway client certificate |

The Cloud Run gateway certificate files are mounted from Google Secret Manager.

The identity that submits Cloud Build needs permission to use GKE, Cloud Run,
and Secret Manager. GKE maintains the managed worker DNS records.
