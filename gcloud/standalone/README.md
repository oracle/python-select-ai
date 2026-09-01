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

## Deploy (and update) the A2A server

```bash
gcloud/standalone/deploy.sh --build
```

On the first deployment, the script prompts for the ADB user, password, and
connect descriptor. It stores them in Secret Manager under names based on the
Cloud Run service, and grants only the runtime service account access. The
container receives the values as `SELECT_AI_USER`, `SELECT_AI_PASSWORD`, and
`SELECT_AI_DB_CONNECT_STRING`; they are never placed in the image or source
tree.

### Optional: Autonomous Database mTLS wallet

The Select AI SDK already supports `wallet_location` and `wallet_password`.
For Cloud Run, pass the path to the downloaded Autonomous Database wallet ZIP
on the first deployment (or when replacing it):

```bash
gcloud/standalone/deploy.sh --wallet-archive /path/to/Wallet_database.zip
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

The default Cloud Run service is `oracle-a2a-agent`. Its default Agent Team,
installed in Oracle Database, is `ORACLE_AI_DATABASE_AGENT`. Override either
with explicit options:

```bash
gcloud/standalone/deploy.sh --service sales-analyst-a2a --a2a-team SALES_ANALYST
```

Use a distinct `--service` value for each A2A team. Each service gets distinct Secret
Manager secret names by default, so credentials remain attached to that A2A
server.

`--max-instances` controls the number of Cloud Run containers. Each container
can use up to 10 Oracle connections by default; change that limit with
`--pool-max-size`, for example `gcloud/standalone/deploy.sh --pool-max-size 20`.

### Update the Select AI SDK or this repository

Update the checkout (or modify its dependency version), then explicitly build
and deploy the new image:

```bash
git pull
gcloud/standalone/deploy.sh --build
```

`--build` creates a freshly tagged image from the current source; without it,
the existing image is reused. Existing database secrets are reused without
prompting. To rotate the ADB credentials, explicitly request it:

```bash
gcloud/standalone/deploy.sh --rotate-db-credentials
```

### What `cloudbuild.yaml` does

`gcloud/standalone/deploy.sh --build` uses `gcloud/standalone/cloudbuild.yaml` to tell Cloud Build to build
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
