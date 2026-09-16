# Standalone Select AI A2A deployment

`gcloud/standalone/deploy.sh` builds or selects a Select AI container image, creates or
updates a private Cloud Run service, and configures its database secrets. Run
it on a machine with the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
installed and authenticated to the target project.

## IAM permissions

The scripts use the active `gcloud` identity. They do not elevate its access.

### Deployer (the active gcloud identity)

| Operation | Required permissions |
| --- | --- |
| Inspect and create the Artifact Registry repository | `artifactregistry.repositories.get`, `artifactregistry.repositories.create` |
| Inspect and create the default runtime service account | `iam.serviceAccounts.get`, `iam.serviceAccounts.create` |
| Deploy or update Cloud Run | `run.services.create`, `run.services.update`, `run.services.get`, `run.operations.get`; `iam.serviceAccounts.actAs` on the runtime service account; `artifactregistry.repositories.downloadArtifacts` on the image repository |
| With `--build`, upload local source, submit, and wait for a build | `storage.buckets.get`, `storage.objects.create` on the configured source-staging bucket; `cloudbuild.builds.create`, `cloudbuild.builds.get`, `serviceusage.services.use` |
| Inspect, create, and add versions to database or wallet secrets | `secretmanager.secrets.get`, `secretmanager.secrets.create`, `secretmanager.versions.add` |
| Grant the runtime account access to those secrets | `secretmanager.secrets.getIamPolicy`, `secretmanager.secrets.setIamPolicy` |
| Grant Gemini Enterprise and the active gcloud identity access to the service | `run.services.getIamPolicy`, `run.services.setIamPolicy` |
| Obtain the project number | `resourcemanager.projects.get` |

### Runtime service account

| Operation | Required permissions |
| --- | --- |
| Read database and wallet secrets while serving requests | `secretmanager.versions.access` |

### Other service identities

| Principal | Operation | Required permissions |
| --- | --- | --- |
| Cloud Build execution service account | With `--build`, push the built image | `artifactregistry.repositories.uploadArtifacts` |
| Gemini Enterprise service agent | Invoke the private Cloud Run service | `run.routes.invoke` |
| Active gcloud identity | Fetch the Agent Card after deployment | `run.routes.invoke` |

The source-staging bucket is Cloud Build's default unless a custom bucket is
configured. Cloud Build also needs access to its build-log destination; the
default same-project build account has that access. If your organization uses
a custom build service account, source bucket, or log bucket, its administrator
must grant the equivalent Cloud Storage permissions on those resources.

Google Cloud references: [Service Usage access control](https://cloud.google.com/service-usage/docs/access-control), [Cloud Run deployment permissions](https://cloud.google.com/run/docs/reference/iam/roles), [Secret Manager access control](https://cloud.google.com/secret-manager/docs/access-control), [Artifact Registry roles](https://cloud.google.com/artifact-registry/docs/access-control), and [Cloud Build roles](https://cloud.google.com/build/docs/iam-roles-permissions).

The rows that set IAM policy are administrative mutations. They are present
because `deploy.sh` creates and rotates secrets and configures private-service
invocation. If your customer deployment identity must not change IAM, provision
the secrets and the `secretmanager.versions.access`/`run.routes.invoke`
permissions beforehand, then
remove those policy-setting commands from the deployment workflow.

## Prerequisite: enable project APIs once

An administrator must enable these APIs once for the project:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  discoveryengine.googleapis.com \
  --project PROJECT_ID
```

## Deploy dynamic standalone

```bash
gcloud/standalone/deploy.sh \
  --connection-mode dynamic \
  --build
```

With no database options, the deployment fixes neither the Connection URL nor
the AI Agent. The generated A2UI form asks each A2A conversation for Connection
URL, username, password, and AI Agent. The resulting database session runs in
an isolated child process and remains bound to the conversation until it
expires. With `--require-oauth`, that binding also includes the authenticated
owner. Dynamic standalone is restricted to one Cloud Run instance because its
session routing is in memory.

Use `--db-dsn-secret NAME` to fix the Connection URL from an existing Secret
Manager secret, and `--a2a-team TEAM` to fix the AI Agent. The generated form
contains only the values that are not fixed. Use `--rotate-db-config` to prompt
for a Connection URL and create or rotate the service's default DSN secret.

| Dynamic deployment options | Generated A2UI fields |
| --- | --- |
| Neither option | Connection URL, Database username, Database password, AI Agent |
| `--db-dsn-secret` only | Database username, Database password, AI Agent |
| `--a2a-team` only | Connection URL, Database username, Database password |
| Both options | Database username, Database password |

### Fix the Connection URL and AI Agent

The following command updates the default dynamic service so every A2A
conversation supplies only its database username and password. If the named
secret does not exist, the script prompts for the Connection URL and creates
it. Later invocations reuse the secret without prompting.

```bash
gcloud/standalone/deploy.sh \
  --project PROJECT_ID \
  --connection-mode dynamic \
  --a2a-team ORACLE_AI_DATABASE_AGENT \
  --db-dsn-secret select-ai-a2a-standalone-dynamic-db-connect-string
```

Add `--rotate-db-config` only when the secret already exists and its Connection
URL must be replaced.

## Choose whether end-user OAuth is required

By default, the service does not require an application OAuth token. Cloud Run
IAM still allows only authorized callers such as Gemini Enterprise to invoke
the private service. Each A2A conversation gets a separate database session,
but the server does not know or verify which human user owns that conversation.

To require verified end-user ownership, add `--require-oauth`:

```bash
gcloud/standalone/deploy.sh \
  --connection-mode dynamic \
  --require-oauth \
  --build
```

In this mode every A2A request must include `Authorization: Bearer ...` and
the session is scoped by both the authenticated owner and the conversation.
When registering the agent, configure Gemini Enterprise end-user OAuth rather
than selecting **Skip & Finish**. Gemini Enterprise automatically sends its
Cloud Run invocation identity in `X-Serverless-Authorization`; end-user OAuth
adds the separate `Authorization` header consumed by `a2a serve`.

The server derives a stable owner from an ID token's `iss` and `sub` claims.
It also accepts opaque OAuth access tokens without storing or logging them,
but a refreshed opaque token starts a new owner/session scope. See
[Register and manage A2A agents](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent#configure-authentication-and-authorization)
for the OAuth registration steps.

### Deploy a separate OAuth-enabled service from an existing image

A new Cloud Run service cannot inherit an image from another service. Resolve
the most recently updated Select AI image directly from Artifact Registry and
construct an immutable digest URI:

```bash
PROJECT_ID=PROJECT_ID
REGION=us-central1
REPOSITORY=select-ai
IMAGE_NAME=select-ai

IMAGE_RECORD="$(gcloud artifacts docker images list \
  "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME" \
  --project "$PROJECT_ID" \
  --include-tags \
  --sort-by='~UPDATE_TIME' \
  --limit=1 \
  --format='csv[no-heading](package,version)')"

if [[ -z "$IMAGE_RECORD" ]]; then
  echo "No Select AI image exists in Artifact Registry." >&2
  exit 1
fi

IMAGE_URI="${IMAGE_RECORD/,/@}"
echo "$IMAGE_URI"
```

Then create a separate service that fixes the Connection URL and AI Agent and
requires end-user OAuth:

```bash
gcloud/standalone/deploy.sh \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --repository "$REPOSITORY" \
  --connection-mode dynamic \
  --service select-ai-a2a-standalone-oauth \
  --a2a-team ORACLE_AI_DATABASE_AGENT \
  --db-dsn-secret select-ai-a2a-standalone-oauth-db-connect-string \
  --require-oauth \
  --image-uri "$IMAGE_URI"
```

On its first invocation, the deployment script prompts for the Connection URL
and creates the service-specific secret. The generated A2UI form contains only
database username and password. Register this service in Gemini Enterprise
with end-user OAuth; selecting **Skip & Finish** causes its requests to fail
with HTTP 401.

## Deploy fixed standalone

```bash
gcloud/standalone/deploy.sh \
  --connection-mode fixed \
  --a2a-team ORACLE_AI_DATABASE_AGENT \
  --build
```

Fixed mode prompts for the ADB connect descriptor, username, and password. It
mounts all three from Secret Manager and creates the existing shared database
pool at server startup. The generated A2UI connection form is skipped.

### Optional: Autonomous Database mTLS wallet

The Select AI SDK already supports `wallet_location` and `wallet_password`.
Wallet configuration is supported only in fixed mode. For Cloud Run, pass the
path to the downloaded Autonomous Database wallet ZIP on the first deployment
(or when replacing it):

```bash
gcloud/standalone/deploy.sh \
  --connection-mode fixed \
  --a2a-team ORACLE_AI_DATABASE_AGENT \
  --wallet-archive /path/to/Wallet_database.zip
```

The script prompts for the wallet password, stores the ZIP and password as
service-specific Secret Manager secrets, and grants access only to the runtime
service account. Cloud Run mounts the ZIP read-only; its A2A launcher expands it
into ephemeral `/tmp` storage before starting the SDK, verifies it contains
`ewallet.pem`, and sets `SELECT_AI_WALLET_LOCATION` to that file's directory.
Do not commit the wallet ZIP or put its contents in the image.

Later deploys reuse the wallet. To replace it, pass `--wallet-archive` again.

The first deployment needs `--build` (or an explicit `--image-uri`). Later
deployments reuse the image already deployed to the service, so changing Cloud
Run configuration or secrets does not create another image. The command
deploys private Cloud Run, sets the final public URL in the Agent Card, grants your active
gcloud identity and Gemini Enterprise Discovery Engine service agent the
`run.routes.invoke` permission for this Cloud Run service.

The default Cloud Run services are `select-ai-a2a-standalone-dynamic` and
`select-ai-a2a-standalone-fixed`, selected by `--connection-mode`. Dynamic mode
has no default AI Agent. Fixed mode requires `--a2a-team` so all four
connection values are complete at startup. Fix either optional dynamic value
with explicit options:

```bash
gcloud/standalone/deploy.sh \
  --connection-mode dynamic \
  --service sales-analyst-a2a \
  --a2a-team SALES_ANALYST
```

Use a distinct `--service` value for each fixed deployment profile. Each
service gets distinct Secret Manager secret names by default, so credentials
remain attached to that A2A server.

`--max-instances` controls the number of Cloud Run containers in fixed mode.
Dynamic mode requires exactly one instance. A fixed-mode container can use up
to 10 Oracle connections by default; change that limit with `--pool-max-size`.

### Update the Select AI SDK or this repository

Update the checkout (or modify its dependency version), then explicitly build
and deploy the new image:

```bash
git pull
gcloud/standalone/deploy.sh --connection-mode dynamic --build
```

`--build` creates a freshly tagged image from the current source; without it,
the existing image is reused. Existing explicitly selected database secrets
are reused without prompting. To configure or rotate the dynamic deployment's
Connection URL, explicitly request it:

```bash
gcloud/standalone/deploy.sh \
  --connection-mode dynamic \
  --rotate-db-config
```

### What `cloudbuild.yaml` does

`gcloud/standalone/deploy.sh --connection-mode MODE --build` uses
`gcloud/standalone/cloudbuild.yaml` to tell Cloud Build to build
`docker/Dockerfile` and push it to Artifact Registry. It is build configuration,
not a command you run. The build context is the repository root, so the image
can install the Select AI source from `pyproject.toml` and `src/`.

### Cloud Build upload contents

Before the build starts, `gcloud builds submit` archives and uploads the
repository root. The root `.gcloudignore` excludes local virtual environments,
generated documentation, test data, caches, credentials, and Git metadata.
Keep `src/`, `pyproject.toml`, `docker/`, and `gcloud/` in the upload; they are
required to build the image. If the upload is unexpectedly large, check local
directories against `.gcloudignore` before running `--build` again.

After a successful deployment, the script prints the A2A Agent Card JSON.
Paste that JSON into Gemini Enterprise to register the private service. The
required Gemini Enterprise invocation permission has already been added.
