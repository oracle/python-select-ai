#!/usr/bin/env bash

# One-time Google Cloud setup for the Select AI A2A server.
# Creates the Artifact Registry repository, runtime service account, and
# Secret Manager secrets. It prompts for database values and never writes
# them to source files.

set -euo pipefail

project_id="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
region="${REGION:-us-central1}"
repository="${REPOSITORY:-select-ai}"
runtime_sa_name="${RUNTIME_SA_NAME:-oracle-a2a-runtime}"
db_user_secret="${DB_USER_SECRET:-select-ai-db-user}"
db_password_secret="${DB_PASSWORD_SECRET:-select-ai-db-password}"
db_dsn_secret="${DB_DSN_SECRET:-select-ai-db-connect-string}"

if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
  echo "Set PROJECT_ID or configure one with: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

runtime_sa="${runtime_sa_name}@${project_id}.iam.gserviceaccount.com"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project="$project_id"

if ! gcloud artifacts repositories describe "$repository" \
  --location="$region" --project="$project_id" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$repository" \
    --repository-format=docker \
    --location="$region" \
    --project="$project_id"
fi

if ! gcloud iam service-accounts describe "$runtime_sa" \
  --project="$project_id" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$runtime_sa_name" \
    --project="$project_id" \
    --display-name="Oracle Select AI A2A runtime"
fi

read -r -p "ADB user: " db_user
read -r -s -p "ADB password: " db_password
echo
read -r -p "ADB connect descriptor: " db_dsn
trap 'unset db_user db_password db_dsn' EXIT

add_secret() {
  local name="$1"
  local value="$2"

  if gcloud secrets describe "$name" --project="$project_id" >/dev/null 2>&1; then
    printf %s "$value" | gcloud secrets versions add "$name" \
      --project="$project_id" --data-file=- >/dev/null
  else
    printf %s "$value" | gcloud secrets create "$name" \
      --project="$project_id" \
      --replication-policy=automatic \
      --data-file=- >/dev/null
  fi

  gcloud secrets add-iam-policy-binding "$name" \
    --project="$project_id" \
    --member="serviceAccount:$runtime_sa" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
}

add_secret "$db_user_secret" "$db_user"
add_secret "$db_password_secret" "$db_password"
add_secret "$db_dsn_secret" "$db_dsn"

cat <<EOF

Bootstrap complete.

Runtime service account: $runtime_sa
Artifact Registry repository: $region-docker.pkg.dev/$project_id/$repository

The first secret versions are version 1. If you rotate a secret later, pass
its new version to deploy-cloud-run.sh using DB_*_SECRET_VERSION.
EOF
