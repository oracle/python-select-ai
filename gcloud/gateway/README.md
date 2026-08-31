# Dynamic gateway deployment

Dynamic gateway mode exposes one public A2A endpoint where each user selects
an Oracle database connection and Select AI team through the A2UI connection
form.

```text
A2A client
    |
Cloud Run gateway
    |
    +-- private VPC --> Consul in GKE
    |
    +-- private VPC --> worker replicas in GKE
                              |
                       session child process
                              |
                         Oracle Database
```

The gateway is the only public A2A application. Consul and workers are a GKE
clustered service: Consul selects a worker for each new dynamic session, and
the chosen worker retains that session's process and Oracle conversation.

## Deploy the complete stack

Run this from the repository root:

```bash
gcloud/gateway/deploy.sh --project PROJECT_ID
```

The script creates the Artifact Registry repository and GKE Autopilot cluster
when they do not already exist. Cloud Build then:

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
  --worker-replicas 3 \
  --network default \
  --subnet default
```

The Cloud Run gateway uses direct VPC egress to reach the internal Consul load
balancer and GKE worker pod addresses. The default one-instance gateway limit
is intentional: gateway A2A task and context/session state is currently in
memory. Workers, rather than the gateway, provide the clustered capacity for
dynamic sessions.

`cloudbuild.yaml` is the complete build and deployment workflow. It supplies
the generated image and Consul endpoint values to the Cloud Run gateway at
deployment time.

## Optional worker mTLS test mode

Local testing does not use mTLS. The default GCloud deployment also keeps the
current private-VPC HTTP worker transport.

For a short-lived GCloud mTLS test, add a private DNS suffix:

```bash
gcloud/gateway/deploy.sh \
  --project PROJECT_ID \
  --enable-worker-mtls \
  --worker-domain workers.select-ai.internal \
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

Workers run as a StatefulSet. Each worker registers its own private DNS name
with Consul, so the gateway still reaches the exact process that owns the
session. Cloud Build creates the corresponding private Cloud DNS A records.

The certificate and DNS records are refreshed by rerunning the deployment.
Because this is a test mode, rerun it after a worker pod is recreated outside a
deployment; its pod IP can change. Do not use this mode for a long-lived
production stack—use a managed workload-certificate and DNS reconciliation
solution there.

### Where the worker certificate files come from

The certificate paths passed to `select-ai a2a worker` are files **inside each
GKE worker container**. They are mounted from Kubernetes Secrets, not files in
this repository or on the machine that runs `deploy.sh`.

```text
deploy.sh
  -> creates the test certificates and stores them in Secret Manager
  -> Cloud Build reads the worker certificate, worker key, and CA certificate
  -> Cloud Build creates Kubernetes Secrets in select-ai-gateway
  -> GKE mounts those Secrets read-only in every worker container
```

The worker pod receives these mounts:

| Container file | Kubernetes Secret | Secret key | Used for |
| --- | --- | --- | --- |
| `/var/run/select-ai-mtls/tls.crt` | `select-ai-worker-server-tls` | `tls.crt` | worker HTTPS server certificate |
| `/var/run/select-ai-mtls/tls.key` | `select-ai-worker-server-tls` | `tls.key` | worker HTTPS private key |
| `/var/run/select-ai-mtls/gateway-ca.crt` | `select-ai-gateway-client-ca` | `ca.crt` | validates the gateway client certificate |

GKE does not read Google Secret Manager at worker request time. Cloud Build
copies the required material into Kubernetes Secrets during deployment, and the
worker certificate files are mounted from those Kubernetes Secrets as read-only
files. For example, to inspect the paths in a running worker (without printing
their contents):

```bash
kubectl -n select-ai-gateway exec select-ai-worker-0 -- \
  ls -l /var/run/select-ai-mtls/
```

The Cloud Run gateway uses a separate direct mount from Google Secret Manager
for its CA, client certificate, and client key.

The identity that submits Cloud Build needs permission to use GKE, Cloud Run,
Cloud DNS, and Secret Manager. Cloud Build also needs the corresponding GKE,
Cloud Run, Cloud DNS, and Secret Manager permissions because it deploys the
workers, refreshes the private DNS records, and mounts the gateway secrets.
