# Google Cloud deployment

This directory separates the three deployment concerns:

```text
bootstrap.sh          one-time project and Secret Manager setup
build-image.sh        source → one generic Artifact Registry image
deploy-cloud-run.sh   existing image → one Cloud Run service/team
```

## 1. One-time setup and secrets

Run:

```bash
gcloud/bootstrap.sh
```

It enables the required APIs, creates the `select-ai` Artifact Registry Docker
repository, creates the `oracle-a2a-runtime` service account, prompts for the
ADB username/password/connect descriptor, and stores them as Secret Manager
secrets. It also grants only that runtime service account access to the
secrets.

The deployed container receives those secrets as:

```text
SELECT_AI_USER
SELECT_AI_PASSWORD
SELECT_AI_DB_CONNECT_STRING
```

## 2. Build the generic image when code changes

Run:

```bash
gcloud/build-image.sh
```

Cloud Build receives the repository source (filtered by `.gcloudignore`) and
uses `gcloud/Dockerfile`. It builds the generic image:

```text
REGION-docker.pkg.dev/PROJECT_ID/select-ai/select-ai-a2a-server:IMAGE_TAG
```

The database team name is not baked into the image.

## 3. Deploy one or more teams from the same image

Use the image URI emitted by `build-image.sh`:

```bash
IMAGE_URI=REGION-docker.pkg.dev/PROJECT_ID/select-ai/select-ai-a2a-server:IMAGE_TAG \
SERVICE=oracle-database-a2a \
A2A_TEAM=ORACLE_AI_DATABASE_AGENT \
gcloud/deploy-cloud-run.sh
```

Deploy another team without rebuilding:

```bash
IMAGE_URI=REGION-docker.pkg.dev/PROJECT_ID/select-ai/select-ai-a2a-server:IMAGE_TAG \
SERVICE=sales-analyst-a2a \
A2A_TEAM=SALES_ANALYST \
gcloud/deploy-cloud-run.sh
```

The deploy script injects the Secret Manager values as Cloud Run environment
variables. It does not upload source code or build an image. After deployment,
it calls `/.well-known/agent-card.json` using
`gcloud auth print-identity-token` and pretty-prints the result. The active
gcloud user therefore needs `roles/run.invoker` on the service.
