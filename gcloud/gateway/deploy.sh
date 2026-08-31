#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# https://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

# Build and deploy the dynamic Select AI gateway stack: Cloud Run gateway plus
# Consul and worker replicas in GKE.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: gcloud/gateway/deploy.sh [options]

Options:
  --project PROJECT           Google Cloud project (defaults to gcloud config)
  --region REGION             Region for GKE, Cloud Run, and Artifact Registry (default: us-central1)
  --cluster NAME              GKE Autopilot cluster name (default: select-ai-a2a-gateway)
  --repository NAME           Artifact Registry Docker repository (default: select-ai)
  --gateway-service NAME      Cloud Run gateway service name (default: select-ai-a2a-gateway)
  --network NAME              VPC network for Cloud Run direct VPC egress (default: default)
  --subnet NAME               VPC subnet for Cloud Run direct VPC egress (default: default)
  --worker-replicas COUNT     GKE worker replica count (default: 2)
  --enable-worker-mtls        Use ephemeral mTLS certificates for gateway-to-worker calls
  --rotate-worker-mtls        Replace the existing worker mTLS CA and certificates
  --worker-domain DOMAIN      Private DNS suffix for workers; required with --enable-worker-mtls
  --worker-dns-zone NAME      Private Cloud DNS zone name (default: select-ai-workers)
  --mtls-cert-validity-days DAYS
                             Gateway and worker certificate lifetime (default: 365)
  --image-tag TAG             Image tag (default: git SHA plus UTC timestamp)
  -h, --help                  Show this help
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
project_id=""
region="us-central1"
cluster="select-ai-a2a-gateway"
repository="select-ai"
gateway_service="select-ai-a2a-gateway"
network="default"
subnet="default"
worker_replicas="2"
enable_worker_mtls="false"
rotate_worker_mtls="false"
worker_domain=""
worker_dns_zone="select-ai-workers"
mtls_cert_validity_days="365"
image_tag=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) project_id="${2:?--project requires a value}"; shift 2 ;;
    --region) region="${2:?--region requires a value}"; shift 2 ;;
    --cluster) cluster="${2:?--cluster requires a value}"; shift 2 ;;
    --repository) repository="${2:?--repository requires a value}"; shift 2 ;;
    --gateway-service) gateway_service="${2:?--gateway-service requires a value}"; shift 2 ;;
    --network) network="${2:?--network requires a value}"; shift 2 ;;
    --subnet) subnet="${2:?--subnet requires a value}"; shift 2 ;;
    --worker-replicas) worker_replicas="${2:?--worker-replicas requires a value}"; shift 2 ;;
    --enable-worker-mtls) enable_worker_mtls="true"; shift ;;
    --rotate-worker-mtls) rotate_worker_mtls="true"; shift ;;
    --worker-domain) worker_domain="${2:?--worker-domain requires a value}"; shift 2 ;;
    --worker-dns-zone) worker_dns_zone="${2:?--worker-dns-zone requires a value}"; shift 2 ;;
    --mtls-cert-validity-days) mtls_cert_validity_days="${2:?--mtls-cert-validity-days requires a value}"; shift 2 ;;
    --image-tag) image_tag="${2:?--image-tag requires a value}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$project_id" ]]; then
  project_id="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
  echo "Pass --project or configure one with: gcloud config set project PROJECT_ID" >&2
  exit 2
fi
if ! [[ "$worker_replicas" =~ ^[1-9][0-9]*$ ]]; then
  echo "--worker-replicas must be a positive integer." >&2
  exit 2
fi
if [[ "$enable_worker_mtls" == "true" && -z "$worker_domain" ]]; then
  echo "--worker-domain is required with --enable-worker-mtls." >&2
  exit 2
fi
if [[ "$rotate_worker_mtls" == "true" && "$enable_worker_mtls" != "true" ]]; then
  echo "--rotate-worker-mtls requires --enable-worker-mtls." >&2
  exit 2
fi
if ! [[ "$mtls_cert_validity_days" =~ ^[1-9][0-9]*$ ]]; then
  echo "--mtls-cert-validity-days must be a positive integer." >&2
  exit 2
fi

image_tag="${image_tag:-$(git -C "$repo_root" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)}"

gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  container.googleapis.com \
  discoveryengine.googleapis.com \
  dns.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  --project="$project_id"

if ! gcloud artifacts repositories describe "$repository" \
  --location="$region" --project="$project_id" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$repository" \
    --repository-format=docker --location="$region" --project="$project_id"
fi

if ! gcloud container clusters describe "$cluster" \
  --location="$region" --project="$project_id" >/dev/null 2>&1; then
  gcloud container clusters create-auto "$cluster" \
    --location="$region" --network="$network" --project="$project_id"
fi

cleanup_mtls() {
  [[ -n "${mtls_dir:-}" ]] && rm -rf "$mtls_dir"
}

if [[ "$enable_worker_mtls" == "true" ]]; then
  create_mtls_material="$rotate_worker_mtls"
  for secret_name in \
    select-ai-gateway-mtls-ca \
    select-ai-gateway-mtls-cert \
    select-ai-gateway-mtls-key \
    select-ai-worker-mtls-cert \
    select-ai-worker-mtls-key; do
    if ! gcloud secrets versions access latest --secret="$secret_name" \
      --project="$project_id" >/dev/null 2>&1; then
      create_mtls_material="true"
    fi
  done
  if [[ "$create_mtls_material" == "true" ]]; then
    trap cleanup_mtls EXIT
    mtls_dir="$(mktemp -d)"
    umask 077
    ca_validity_days="$((mtls_cert_validity_days + 1))"
    openssl req -x509 -newkey rsa:2048 -nodes -days "$ca_validity_days" \
      -keyout "$mtls_dir/ca.key" -out "$mtls_dir/ca.crt" \
      -subj "/CN=select-ai ephemeral worker CA" >/dev/null 2>&1
    openssl req -newkey rsa:2048 -nodes \
      -keyout "$mtls_dir/worker.key" -out "$mtls_dir/worker.csr" \
      -subj "/CN=*.$worker_domain" >/dev/null 2>&1
    printf 'subjectAltName=DNS:*.%s\nextendedKeyUsage=serverAuth\n' "$worker_domain" \
      > "$mtls_dir/worker.ext"
    openssl x509 -req -days "$mtls_cert_validity_days" -in "$mtls_dir/worker.csr" \
      -CA "$mtls_dir/ca.crt" -CAkey "$mtls_dir/ca.key" -CAcreateserial \
      -out "$mtls_dir/worker.crt" -extfile "$mtls_dir/worker.ext" >/dev/null 2>&1
    openssl req -newkey rsa:2048 -nodes \
      -keyout "$mtls_dir/gateway.key" -out "$mtls_dir/gateway.csr" \
      -subj "/CN=select-ai-gateway" >/dev/null 2>&1
    printf 'extendedKeyUsage=clientAuth\n' > "$mtls_dir/gateway.ext"
    openssl x509 -req -days "$mtls_cert_validity_days" -in "$mtls_dir/gateway.csr" \
      -CA "$mtls_dir/ca.crt" -CAkey "$mtls_dir/ca.key" -CAcreateserial \
      -out "$mtls_dir/gateway.crt" -extfile "$mtls_dir/gateway.ext" >/dev/null 2>&1
    for secret_name in \
      select-ai-gateway-mtls-ca \
      select-ai-gateway-mtls-cert \
      select-ai-gateway-mtls-key \
      select-ai-worker-mtls-cert \
      select-ai-worker-mtls-key; do
      gcloud secrets describe "$secret_name" --project="$project_id" >/dev/null 2>&1 || \
        gcloud secrets create "$secret_name" --replication-policy=automatic --project="$project_id"
    done
    gcloud secrets versions add select-ai-gateway-mtls-ca --data-file="$mtls_dir/ca.crt" --project="$project_id"
    gcloud secrets versions add select-ai-gateway-mtls-cert --data-file="$mtls_dir/gateway.crt" --project="$project_id"
    gcloud secrets versions add select-ai-gateway-mtls-key --data-file="$mtls_dir/gateway.key" --project="$project_id"
    gcloud secrets versions add select-ai-worker-mtls-cert --data-file="$mtls_dir/worker.crt" --project="$project_id"
    gcloud secrets versions add select-ai-worker-mtls-key --data-file="$mtls_dir/worker.key" --project="$project_id"
    if [[ "$rotate_worker_mtls" == "true" ]]; then
      echo "Rotating worker mTLS material; worker sessions will be interrupted."
    else
      echo "Created initial worker mTLS material."
    fi
  else
    echo "Reusing existing worker mTLS material."
  fi
  if ! gcloud dns managed-zones describe "$worker_dns_zone" --project="$project_id" >/dev/null 2>&1; then
    gcloud dns managed-zones create "$worker_dns_zone" --dns-name="${worker_domain}." \
      --visibility=private --networks="https://www.googleapis.com/compute/v1/projects/$project_id/global/networks/$network" \
      --description="Private DNS records for Select AI mTLS workers" \
      --project="$project_id"
  fi
  runtime_sa="${project_id_number:-$(gcloud projects describe "$project_id" --format='value(projectNumber)')}-compute@developer.gserviceaccount.com"
  for secret_name in \
    select-ai-gateway-mtls-ca \
    select-ai-gateway-mtls-cert \
    select-ai-gateway-mtls-key \
    select-ai-worker-mtls-cert \
    select-ai-worker-mtls-key; do
    gcloud secrets add-iam-policy-binding "$secret_name" --project="$project_id" \
      --member="serviceAccount:$runtime_sa" --role="roles/secretmanager.secretAccessor" >/dev/null
  done
fi

gcloud builds submit "$repo_root" \
  --project="$project_id" \
  --region="$region" \
  --config="$repo_root/gcloud/gateway/cloudbuild.yaml" \
  --substitutions="_REGION=$region,_CLUSTER=$cluster,_REPOSITORY=$repository,_IMAGE_TAG=$image_tag,_GATEWAY_SERVICE=$gateway_service,_NETWORK=$network,_SUBNET=$subnet,_WORKER_REPLICAS=$worker_replicas,_ENABLE_WORKER_MTLS=$enable_worker_mtls,_ROTATE_WORKER_MTLS=$rotate_worker_mtls,_WORKER_DOMAIN=$worker_domain,_WORKER_DNS_ZONE=$worker_dns_zone"

gateway_url="$(gcloud run services describe "$gateway_service" \
  --region="$region" --project="$project_id" --format='value(status.url)')"
project_number="$(gcloud projects describe "$project_id" --format='value(projectNumber)')"
gemini_service_agent="service-$project_number@gcp-sa-discoveryengine.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding "$gateway_service" \
  --region="$region" --project="$project_id" \
  --member="serviceAccount:$gemini_service_agent" \
  --role="roles/run.invoker" >/dev/null

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
if [[ -z "$active_account" ]]; then
  echo "No active gcloud account. Run: gcloud auth login" >&2
  exit 2
fi
if gcloud iam service-accounts describe "$active_account" \
  --project="$project_id" >/dev/null 2>&1; then
  deployer_member="serviceAccount:$active_account"
else
  deployer_member="user:$active_account"
fi
gcloud run services add-iam-policy-binding "$gateway_service" \
  --region="$region" --project="$project_id" \
  --member="$deployer_member" --role="roles/run.invoker" >/dev/null

printf 'Gateway Agent Card URL:\n%s/.well-known/agent-card.json\n' "$gateway_url"
