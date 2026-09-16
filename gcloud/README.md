# Google Cloud deployment modes

Select AI for Python supports three Google Cloud A2A deployment profiles. The
profiles keep deployment topology separate from connection provisioning:

1. **Fixed standalone** runs one Cloud Run service with DSN, username,
   password, and team fixed by deployment. It uses the shared connection pool
   and supports streaming.
2. **Dynamic standalone** runs one Cloud Run service. Connection URL and AI
   Agent may be fixed independently by deployment; each user supplies all
   remaining connection values through A2UI and receives an isolated
   child-process session. Its in-memory routing requires exactly one Cloud Run
   instance and streaming is disabled.
3. **Clustered dynamic** runs the same public A2A contract on Cloud Run, with
   Consul and workers on GKE. DSN and team are fixed; each user supplies
   username and password through A2UI. Consul provides distributed routing and
   workers own the isolated session processes.

![Select AI A2A deployment architecture](../doc/source/image/a2a_architecture.svg)

The A2A commands are cloud-neutral. These scripts are optional Google Cloud
automation for the Cloud Run and GKE profiles.

## Standalone deployments

Use the same script with an explicit connection mode.

Dynamic standalone:

```bash
gcloud/standalone/deploy.sh \
  --project PROJECT_ID \
  --connection-mode dynamic \
  --build
```

Fixed standalone:

```bash
gcloud/standalone/deploy.sh \
  --project PROJECT_ID \
  --connection-mode fixed \
  --a2a-team ORACLE_AI_DATABASE_AGENT \
  --build
```

The modes use distinct default services:

- `select-ai-a2a-standalone-dynamic`
- `select-ai-a2a-standalone-fixed`

See the [standalone deployment guide](standalone/README.md).

The standalone guide also shows how to select the newest existing image
directly from Artifact Registry by immutable digest. Use that workflow when
creating another Cloud Run service without rebuilding an identical image or
depending on an existing service as the image source.

## Clustered dynamic deployment

```bash
gcloud/cluster/deploy.sh --project PROJECT_ID
```

Pass `--image-uri IMAGE@sha256:DIGEST` to reuse an existing immutable image
for both the Cloud Run server and GKE workers instead of building another one.

The default GKE cluster and public Cloud Run service are both named
`select-ai-a2a-cluster` in their respective resource namespaces. The server uses direct VPC egress to
reach Consul and the GKE workers. The worker transport is private HTTP by
default; optional mTLS protects the server-to-worker hop. Wallet-based Oracle
Database mTLS is not yet supported for dynamic sessions.

See the [cluster deployment guide](cluster/README.md).

## Client-visible differences

| Concern | Fixed standalone | Dynamic standalone | Clustered dynamic |
| --- | --- | --- | --- |
| Topology | Cloud Run | One Cloud Run instance | Cloud Run + Consul + GKE workers |
| Deployment-fixed values | Connection URL, username, password, AI Agent | Any subset of Connection URL and AI Agent | Connection URL and AI Agent |
| A2UI form | None | All connection values not fixed by deployment | Username and password |
| Database runtime | Shared configured pool | Isolated local child process | Isolated worker child process |
| Streaming | Supported | Not currently supported | Not currently supported |
| Task/context storage | Oracle Database | Oracle Database | Oracle Database with Consul routing metadata |
| Scaling | Cloud Run instances and pool size | One Cloud Run instance | Cloud Run instances and worker replicas |

All three expose:

```text
/.well-known/agent-card.json
/a2a/jsonrpc/
```

They accept A2A 1.0 method names and the A2A v0.3 compatibility method names.
The connection-form client flow is documented in the
[dynamic-session samples](../samples/a2a/dynamic/README.md).

By default, the private Cloud Run deployments rely on Cloud Run IAM and keep
database sessions separate by A2A conversation. Add `--require-oauth` to
either deployment script when verified human-user ownership is required. In
that mode Gemini Enterprise must be configured with end-user OAuth and sends
its user token in `Authorization`; missing tokens receive HTTP 401.

`X-Serverless-Authorization` is separate and automatic: Gemini Enterprise uses
it to invoke the private Cloud Run service, and Cloud Run consumes it before
the request reaches `a2a serve`.
