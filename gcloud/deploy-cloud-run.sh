#!/usr/bin/env bash

# Deploy an existing Select AI A2A server image to private Cloud Run.
#
# Prerequisites:
#   * gcloud is authenticated and has deployment permissions.
#   * Run bootstrap.sh to create the runtime service account and secrets.
#   * Run build-image.sh to create IMAGE_URI when application code changes.
#
# Override any setting by exporting it before running this script.

set -euo pipefail

project_id="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
region="${REGION:-us-central1}"
service="${SERVICE:-oracle-a2a-agent}"
a2a_team="${A2A_TEAM:-ORACLE_AI_DATABASE_AGENT}"
runtime_sa="${RUNTIME_SA:-oracle-a2a-runtime@${project_id}.iam.gserviceaccount.com}"
image_uri="${IMAGE_URI:-}"
db_user_secret="${DB_USER_SECRET:-select-ai-db-user}"
db_password_secret="${DB_PASSWORD_SECRET:-select-ai-db-password}"
db_dsn_secret="${DB_DSN_SECRET:-select-ai-db-connect-string}"
memory="${MEMORY:-1Gi}"
timeout="${TIMEOUT:-900}"
max_instances="${MAX_INSTANCES:-1}"

if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
  echo "Set PROJECT_ID or configure one with: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

if [[ -z "$image_uri" ]]; then
  echo "Set IMAGE_URI to an image created by gcloud/build-image.sh" >&2
  exit 1
fi

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
if [[ -z "$active_account" ]]; then
  echo "No active gcloud account. Run: gcloud auth login" >&2
  exit 1
fi

for secret in "$db_user_secret" "$db_password_secret" "$db_dsn_secret"; do
  gcloud secrets describe "$secret" --project="$project_id" >/dev/null
done

gcloud iam service-accounts describe "$runtime_sa" \
  --project="$project_id" >/dev/null

# The entrypoint requires PUBLIC_URL. This first revision is immediately
# followed by an update using the actual URL returned by Cloud Run.
gcloud run deploy "$service" \
  --image="$image_uri" \
  --project="$project_id" \
  --region="$region" \
  --service-account="$runtime_sa" \
  --no-allow-unauthenticated \
  --port=8080 \
  --memory="$memory" \
  --timeout="$timeout" \
  --max-instances="$max_instances" \
  --set-env-vars="A2A_TEAM=$a2a_team,PUBLIC_URL=https://pending.invalid" \
  --update-secrets="SELECT_AI_USER=$db_user_secret:1,SELECT_AI_PASSWORD=$db_password_secret:1,SELECT_AI_DB_CONNECT_STRING=$db_dsn_secret:1"

service_url="$(gcloud run services describe "$service" \
  --project="$project_id" \
  --region="$region" \
  --format='value(status.url)')"

gcloud run services update "$service" \
  --project="$project_id" \
  --region="$region" \
  --update-env-vars="PUBLIC_URL=$service_url"

echo "Fetching the authenticated A2A Agent Card..."
agent_card="$(curl --fail --silent --show-error \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$service_url/.well-known/agent-card.json")"

printf '%s\n' "$agent_card" | python3 -m json.tool

cat <<EOF

Deployment complete.

Cloud Run URL: $service_url

Generate the Gemini Enterprise A2A v0.3 Agent Card:
  select-ai a2a agent-card --team "$a2a_team" --public-url "$service_url"

Before Gemini Enterprise can invoke this private service, grant its Discovery
Engine service agent roles/run.invoker on this Cloud Run service.
EOF
