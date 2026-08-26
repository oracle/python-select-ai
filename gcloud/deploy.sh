#!/usr/bin/env bash

# Deploy one Select AI A2A server to private Cloud Run. On its first run it
# creates the ADB secrets used by this service. Later runs reuse both those
# secrets and the service's currently deployed image.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: gcloud/deploy.sh [options]

Deploy the Select AI A2A server to private Cloud Run.

Options:
  --project PROJECT              Google Cloud project (defaults to gcloud config project)
  --region REGION                Cloud Run and Artifact Registry region (default: us-central1)
  --repository REPOSITORY        Docker repository name (default: select-ai)
  --service SERVICE              Cloud Run service name (default: oracle-a2a-agent)
  --a2a-team TEAM                Agent Team installed in Oracle Database (default: ORACLE_AI_DATABASE_AGENT)
  --runtime-sa EMAIL             Runtime service-account email
  --runtime-sa-name NAME         Default runtime service-account name (default: oracle-a2a-runtime)
  --db-user-secret NAME          Secret name for the ADB user
  --db-password-secret NAME      Secret name for the ADB password
  --db-dsn-secret NAME           Secret name for the ADB connect descriptor
  --wallet-secret NAME           Secret name for the wallet archive
  --wallet-password-secret NAME  Secret name for the wallet password
  --wallet-archive PATH          Wallet ZIP to upload or replace
  --memory MEMORY                Cloud Run memory limit (default: 1Gi)
  --timeout SECONDS              Cloud Run request timeout (default: 900)
  --max-instances COUNT          Cloud Run maximum instances (default: 1)
  --pool-max-size COUNT          Maximum Oracle connections per instance (default: 10)
  --image-uri URI                Deploy this container image
  --build                        Build the current checkout before deploying
  --image-tag TAG                Tag for --build (default: git SHA plus UTC timestamp)
  --rotate-db-credentials        Prompt for and rotate ADB credentials
  -h, --help                     Show this help
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_id=""
region="us-central1"
repository="select-ai"
service="oracle-a2a-agent"
a2a_team="ORACLE_AI_DATABASE_AGENT"
runtime_sa=""
runtime_sa_name="oracle-a2a-runtime"
runtime_sa_explicit=false
db_user_secret=""
db_password_secret=""
db_dsn_secret=""
wallet_secret=""
wallet_password_secret=""
wallet_archive=""
memory="1Gi"
timeout="900"
max_instances="1"
pool_max_size="10"
image_uri=""
image_tag=""
build_image=false
rotate_db_credentials=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) project_id="${2:?--project requires a value}"; shift 2 ;;
    --region) region="${2:?--region requires a value}"; shift 2 ;;
    --repository) repository="${2:?--repository requires a value}"; shift 2 ;;
    --service) service="${2:?--service requires a value}"; shift 2 ;;
    --a2a-team) a2a_team="${2:?--a2a-team requires a value}"; shift 2 ;;
    --runtime-sa) runtime_sa="${2:?--runtime-sa requires a value}"; runtime_sa_explicit=true; shift 2 ;;
    --runtime-sa-name) runtime_sa_name="${2:?--runtime-sa-name requires a value}"; shift 2 ;;
    --db-user-secret) db_user_secret="${2:?--db-user-secret requires a value}"; shift 2 ;;
    --db-password-secret) db_password_secret="${2:?--db-password-secret requires a value}"; shift 2 ;;
    --db-dsn-secret) db_dsn_secret="${2:?--db-dsn-secret requires a value}"; shift 2 ;;
    --wallet-secret) wallet_secret="${2:?--wallet-secret requires a value}"; shift 2 ;;
    --wallet-password-secret) wallet_password_secret="${2:?--wallet-password-secret requires a value}"; shift 2 ;;
    --wallet-archive) wallet_archive="${2:?--wallet-archive requires a value}"; shift 2 ;;
    --memory) memory="${2:?--memory requires a value}"; shift 2 ;;
    --timeout) timeout="${2:?--timeout requires a value}"; shift 2 ;;
    --max-instances) max_instances="${2:?--max-instances requires a value}"; shift 2 ;;
    --pool-max-size) pool_max_size="${2:?--pool-max-size requires a value}"; shift 2 ;;
    --image-uri) image_uri="${2:?--image-uri requires a value}"; shift 2 ;;
    --build) build_image=true; shift ;;
    --image-tag) image_tag="${2:?--image-tag requires a value}"; shift 2 ;;
    --rotate-db-credentials) rotate_db_credentials=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$project_id" ]]; then
  project_id="$(gcloud config get-value project 2>/dev/null || true)"
fi

if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
  echo "Pass --project or configure one with: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

runtime_sa="${runtime_sa:-${runtime_sa_name}@${project_id}.iam.gserviceaccount.com}"
db_user_secret="${db_user_secret:-${service}-db-user}"
db_password_secret="${db_password_secret:-${service}-db-password}"
db_dsn_secret="${db_dsn_secret:-${service}-db-connect-string}"
wallet_secret="${wallet_secret:-${service}-wallet}"
wallet_password_secret="${wallet_password_secret:-${service}-wallet-password}"

if [[ "$build_image" == true && -n "$image_uri" ]]; then
  echo "--build and --image-uri cannot be used together." >&2
  exit 2
fi
if [[ "$build_image" == false && -n "$image_tag" ]]; then
  echo "--image-tag requires --build." >&2
  exit 2
fi
if ! [[ "$pool_max_size" =~ ^[1-9][0-9]*$ ]]; then
  echo "--pool-max-size must be a positive integer." >&2
  exit 2
fi

if ! gcloud artifacts repositories describe "$repository" --location="$region" \
  --project="$project_id" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$repository" \
    --repository-format=docker --location="$region" --project="$project_id"
fi

if ! gcloud iam service-accounts describe "$runtime_sa" --project="$project_id" >/dev/null 2>&1; then
  if [[ "$runtime_sa_explicit" == true ]]; then
    echo "Runtime service account does not exist: $runtime_sa" >&2
    exit 1
  fi
  gcloud iam service-accounts create "$runtime_sa_name" --project="$project_id" \
    --display-name="Oracle Select AI A2A runtime"
fi

# Deployments made with the former scripts used these shared secret names.
# Reuse them automatically so an existing service can be updated without
# re-entering credentials. New services receive service-specific names above.
service_exists=false
if gcloud run services describe "$service" --project="$project_id" --region="$region" >/dev/null 2>&1; then
  service_exists=true
fi

create_or_rotate_secrets=false
if [[ "$rotate_db_credentials" == true ]]; then
  create_or_rotate_secrets=true
else
  for secret in "$db_user_secret" "$db_password_secret" "$db_dsn_secret"; do
    if ! gcloud secrets describe "$secret" --project="$project_id" >/dev/null 2>&1; then
      create_or_rotate_secrets=true
      break
    fi
  done
fi

if [[ "$create_or_rotate_secrets" == true ]]; then
  echo "Creating or rotating ADB credentials for Cloud Run service: $service"
  read -r -p "ADB user: " db_user
  read -r -s -p "ADB password: " db_password
  echo
  read -r -p "ADB connect descriptor: " db_dsn
  trap 'unset db_user db_password db_dsn' EXIT

  add_secret() {
    local name="$1"
    local value="$2"
    if gcloud secrets describe "$name" --project="$project_id" >/dev/null 2>&1; then
      printf %s "$value" | gcloud secrets versions add "$name" --project="$project_id" --data-file=- >/dev/null
    else
      printf %s "$value" | gcloud secrets create "$name" --project="$project_id" --replication-policy=automatic --data-file=- >/dev/null
    fi
    gcloud secrets add-iam-policy-binding "$name" --project="$project_id" \
      --member="serviceAccount:$runtime_sa" --role="roles/secretmanager.secretAccessor" >/dev/null
  }

  add_secret "$db_user_secret" "$db_user"
  add_secret "$db_password_secret" "$db_password"
  add_secret "$db_dsn_secret" "$db_dsn"
fi

# An Oracle mTLS wallet is a ZIP archive containing several files, so it is
# mounted as a Secret Manager volume rather than exposed as an environment
# variable. Pass --wallet-archive to enable or replace this optional configuration.
wallet_enabled=false
if gcloud secrets describe "$wallet_secret" --project="$project_id" >/dev/null 2>&1 \
  && gcloud secrets describe "$wallet_password_secret" --project="$project_id" >/dev/null 2>&1; then
  wallet_enabled=true
fi
if [[ -n "$wallet_archive" ]]; then
  if [[ ! -f "$wallet_archive" ]]; then
    echo "--wallet-archive must name an existing wallet ZIP file: $wallet_archive" >&2
    exit 1
  fi
  read -r -s -p "ADB wallet password: " wallet_password
  echo
  trap 'unset db_user db_password db_dsn wallet_password' EXIT

  if gcloud secrets describe "$wallet_secret" --project="$project_id" >/dev/null 2>&1; then
    gcloud secrets versions add "$wallet_secret" --project="$project_id" --data-file="$wallet_archive" >/dev/null
  else
    gcloud secrets create "$wallet_secret" --project="$project_id" --replication-policy=automatic --data-file="$wallet_archive" >/dev/null
  fi
  if gcloud secrets describe "$wallet_password_secret" --project="$project_id" >/dev/null 2>&1; then
    printf %s "$wallet_password" | gcloud secrets versions add "$wallet_password_secret" --project="$project_id" --data-file=- >/dev/null
  else
    printf %s "$wallet_password" | gcloud secrets create "$wallet_password_secret" --project="$project_id" --replication-policy=automatic --data-file=- >/dev/null
  fi
  wallet_enabled=true
fi
if [[ "$wallet_enabled" == true ]]; then
  for secret in "$wallet_secret" "$wallet_password_secret"; do
    gcloud secrets add-iam-policy-binding "$secret" --project="$project_id" \
      --member="serviceAccount:$runtime_sa" --role="roles/secretmanager.secretAccessor" >/dev/null
  done
fi

if [[ "$build_image" == true ]]; then
  image_tag="${image_tag:-$(git -C "$repo_root" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)}"
  image_uri="$region-docker.pkg.dev/$project_id/$repository/select-ai:$image_tag"
  echo "Building $image_uri"
  gcloud builds submit "$repo_root" --project="$project_id" \
    --config="$repo_root/gcloud/cloudbuild.yaml" \
    --substitutions="_REGION=$region,_REPOSITORY=$repository,_IMAGE_TAG=$image_tag"
elif [[ -z "$image_uri" && "$service_exists" == true ]]; then
  image_uri="$(gcloud run services describe "$service" --project="$project_id" --region="$region" \
    --format='value(spec.template.spec.containers[0].image)')"
elif [[ -z "$image_uri" ]]; then
  echo "First deployment requires --build or --image-uri." >&2
  exit 2
fi

# Cloud Run needs a URL before the server can construct its Agent Card. Deploy
# once with a placeholder, then update PUBLIC_URL with the assigned URL.
secret_mappings=(
  "SELECT_AI_USER=$db_user_secret:latest"
  "SELECT_AI_PASSWORD=$db_password_secret:latest"
  "SELECT_AI_DB_CONNECT_STRING=$db_dsn_secret:latest"
)
if [[ "$wallet_enabled" == true ]]; then
  secret_mappings+=(
    "/var/run/secrets/select-ai-wallet/wallet.zip=$wallet_secret:latest"
    "SELECT_AI_WALLET_PASSWORD=$wallet_password_secret:latest"
  )
fi
secret_mappings_csv="$(IFS=,; echo "${secret_mappings[*]}")"

gcloud run deploy "$service" --image="$image_uri" --project="$project_id" --region="$region" \
  --service-account="$runtime_sa" --no-allow-unauthenticated --port=8080 \
  --command="/app/docker/a2a-entrypoint.sh" \
  --memory="$memory" --timeout="$timeout" --max-instances="$max_instances" \
  --set-env-vars="SELECT_AI_A2A_TEAM=$a2a_team,PUBLIC_URL=https://pending.invalid,SELECT_AI_POOL_MAX_SIZE=$pool_max_size" \
  --update-secrets="$secret_mappings_csv"

service_url="$(gcloud run services describe "$service" --project="$project_id" --region="$region" --format='value(status.url)')"
gcloud run services update "$service" --project="$project_id" --region="$region" --update-env-vars="PUBLIC_URL=$service_url"

project_number="$(gcloud projects describe "$project_id" --format='value(projectNumber)')"
gemini_sa="service-$project_number@gcp-sa-discoveryengine.iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding "$service" --project="$project_id" --region="$region" \
  --member="serviceAccount:$gemini_sa" --role="roles/run.invoker" >/dev/null

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
if [[ -z "$active_account" ]]; then
  echo "No active gcloud account. Run: gcloud auth login" >&2
  exit 1
fi
if gcloud iam service-accounts describe "$active_account" --project="$project_id" >/dev/null 2>&1; then
  deployer_member="serviceAccount:$active_account"
else
  deployer_member="user:$active_account"
fi
gcloud run services add-iam-policy-binding "$service" --project="$project_id" --region="$region" \
  --member="$deployer_member" --role="roles/run.invoker" >/dev/null

echo "Cloud Run URL: $service_url"
echo "Fetching the authenticated A2A Agent Card..."
agent_card_file="$(mktemp)"
trap 'rm -f "$agent_card_file"' EXIT
if ! curl --fail --silent --show-error \
  --retry 12 --retry-all-errors --retry-delay 5 --retry-max-time 120 \
  --connect-timeout 10 --max-time 30 \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  --output "$agent_card_file" \
  "$service_url/.well-known/agent-card.json"; then
  echo "Unable to fetch the A2A Agent Card after waiting for Cloud Run to become available." >&2
  exit 1
fi
python3 -m json.tool < "$agent_card_file"

cat <<EOF

Deployment complete.

Cloud Run URL: $service_url
Gemini Enterprise invoker: $gemini_sa

Paste this A2A v0.3 Agent Card into Gemini Enterprise:
  select-ai a2a agent-card --team "$a2a_team" --public-url "$service_url"
EOF
