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
  --region REGION             Region for GKE, Cloud Run, and Artifact Registry
                              (default: us-central1)
  --cluster NAME              GKE Autopilot cluster name (default: select-ai-a2a-gateway)
  --gke-dns-domain DOMAIN    Unique GKE additive VPC DNS domain
                              (default: select-ai-a2a-gateway.internal)
  --repository NAME           Artifact Registry Docker repository (default: select-ai)
  --gateway-service NAME      Cloud Run gateway service name (default: select-ai-a2a-gateway)
  --network NAME              VPC network for Cloud Run direct VPC egress (default: default)
  --subnet NAME               VPC subnet for Cloud Run direct VPC egress (default: default)
  --worker-replicas COUNT     GKE worker replica count (default: 2)
  --session-ttl-seconds N    Dynamic session lifetime (default: 900)
  --enable-worker-mtls        Use ephemeral mTLS certificates for gateway-to-worker calls
  --rotate-worker-mtls        Replace the existing worker mTLS CA and certificates
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
gke_dns_domain="select-ai-a2a-gateway.internal"
repository="select-ai"
gateway_service="select-ai-a2a-gateway"
network="default"
subnet="default"
worker_replicas="2"
session_ttl_seconds="900"
enable_worker_mtls="false"
rotate_worker_mtls="false"
mtls_cert_validity_days="365"
image_tag=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) project_id="${2:?--project requires a value}"; shift 2 ;;
    --region) region="${2:?--region requires a value}"; shift 2 ;;
    --cluster) cluster="${2:?--cluster requires a value}"; shift 2 ;;
    --gke-dns-domain) gke_dns_domain="${2:?--gke-dns-domain requires a value}"; shift 2 ;;
    --repository) repository="${2:?--repository requires a value}"; shift 2 ;;
    --gateway-service) gateway_service="${2:?--gateway-service requires a value}"; shift 2 ;;
    --network) network="${2:?--network requires a value}"; shift 2 ;;
    --subnet) subnet="${2:?--subnet requires a value}"; shift 2 ;;
    --worker-replicas) worker_replicas="${2:?--worker-replicas requires a value}"; shift 2 ;;
    --session-ttl-seconds)
      session_ttl_seconds="${2:?--session-ttl-seconds requires a value}"
      shift 2
      ;;
    --enable-worker-mtls) enable_worker_mtls="true"; shift ;;
    --rotate-worker-mtls) rotate_worker_mtls="true"; shift ;;
    --mtls-cert-validity-days)
      mtls_cert_validity_days="${2:?--mtls-cert-validity-days requires a value}"
      shift 2
      ;;
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
if ! [[ "$session_ttl_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "--session-ttl-seconds must be a positive integer." >&2
  exit 2
fi
if [[ -z "$gke_dns_domain" || "$gke_dns_domain" == *.local ]]; then
  echo "--gke-dns-domain must be non-empty and must not end in .local." >&2
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
    --location="$region" --network="$network" --subnetwork="$subnet" \
    --additive-vpc-scope-dns-domain="$gke_dns_domain" --project="$project_id"
else
  configured_dns_domain="$(gcloud container clusters describe "$cluster" \
    --location="$region" --project="$project_id" \
    --format='value(networkConfig.dnsConfig.additiveVpcScopeDnsDomain)')"
  if [[ "$configured_dns_domain" != "$gke_dns_domain" ]]; then
    echo "Cluster $cluster does not use additive VPC DNS domain $gke_dns_domain." >&2
    echo "Create a replacement cluster or pass its configured --gke-dns-domain." >&2
    exit 2
  fi
fi

project_number="$(gcloud projects describe "$project_id" \
  --format='value(projectNumber)')"

cleanup_mtls() {
  [[ -n "${mtls_dir:-}" ]] && rm -rf "$mtls_dir"
}

if [[ "$enable_worker_mtls" == "true" ]]; then
  create_mtls_material="$rotate_worker_mtls"
  worker_certificate_dns_name="*.select-ai-worker.select-ai-gateway.svc.$gke_dns_domain"
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
  if [[ "$create_mtls_material" != "true" ]]; then
    # macOS ships LibreSSL, which does not support x509's -ext option.
    # Read the portable text representation and perform a literal SAN check.
    existing_worker_certificate_text="$(
      gcloud secrets versions access latest \
        --secret=select-ai-worker-mtls-cert --project="$project_id" 2>/dev/null | \
      openssl x509 -noout -text 2>/dev/null || true
    )"
    if ! printf '%s\n' "$existing_worker_certificate_text" | \
      grep -F -- "DNS:$worker_certificate_dns_name" >/dev/null; then
      create_mtls_material="true"
      echo "Replacing mTLS material because the worker certificate does not"
      echo "match the GKE DNS domain."
    fi
  fi
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
      -subj "/CN=select-ai-worker" >/dev/null 2>&1
    printf 'subjectAltName=DNS:%s\nextendedKeyUsage=serverAuth\n' "$worker_certificate_dns_name" \
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
    gcloud secrets versions add select-ai-gateway-mtls-ca \
      --data-file="$mtls_dir/ca.crt" --project="$project_id"
    gcloud secrets versions add select-ai-gateway-mtls-cert \
      --data-file="$mtls_dir/gateway.crt" --project="$project_id"
    gcloud secrets versions add select-ai-gateway-mtls-key \
      --data-file="$mtls_dir/gateway.key" --project="$project_id"
    gcloud secrets versions add select-ai-worker-mtls-cert \
      --data-file="$mtls_dir/worker.crt" --project="$project_id"
    gcloud secrets versions add select-ai-worker-mtls-key \
      --data-file="$mtls_dir/worker.key" --project="$project_id"
    if [[ "$rotate_worker_mtls" == "true" ]]; then
      echo "Rotating worker mTLS material; worker sessions will be interrupted."
    else
      echo "Created initial worker mTLS material."
    fi
  else
    echo "Reusing existing worker mTLS material."
  fi
  runtime_sa="${project_number}-compute@developer.gserviceaccount.com"
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

build_substitutions=(
  "_REGION=$region"
  "_CLUSTER=$cluster"
  "_REPOSITORY=$repository"
  "_IMAGE_TAG=$image_tag"
  "_GATEWAY_SERVICE=$gateway_service"
  "_NETWORK=$network"
  "_SUBNET=$subnet"
  "_WORKER_REPLICAS=$worker_replicas"
  "_SESSION_TTL_SECONDS=$session_ttl_seconds"
  "_ENABLE_WORKER_MTLS=$enable_worker_mtls"
  "_ROTATE_WORKER_MTLS=$rotate_worker_mtls"
  "_GKE_DNS_DOMAIN=$gke_dns_domain"
)

gcloud builds submit "$repo_root" \
  --project="$project_id" \
  --region="$region" \
  --config="$repo_root/gcloud/gateway/cloudbuild.yaml" \
  --substitutions="$(IFS=,; printf '%s' "${build_substitutions[*]}")"

gateway_url="$(gcloud run services describe "$gateway_service" \
  --region="$region" --project="$project_id" --format='value(status.url)')"
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
