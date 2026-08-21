#!/usr/bin/env bash

# Build the reusable Select AI A2A server image from the repository source.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_id="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
region="${REGION:-us-central1}"
repository="${REPOSITORY:-select-ai}"
image_tag="${IMAGE_TAG:-$(git -C "$repo_root" rev-parse --short HEAD)}"

if [[ -z "$project_id" || "$project_id" == "(unset)" ]]; then
  echo "Set PROJECT_ID or configure one with: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

gcloud builds submit "$repo_root" \
  --project="$project_id" \
  --config="$repo_root/gcloud/cloudbuild.yaml" \
  --substitutions="_REGION=$region,_REPOSITORY=$repository,_IMAGE_TAG=$image_tag"

echo "$region-docker.pkg.dev/$project_id/$repository/select-ai-a2a-server:$image_tag"
