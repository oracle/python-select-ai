#!/usr/bin/env sh

set -eu

: "${A2A_TEAM:?A2A_TEAM is required}"
: "${PUBLIC_URL:?PUBLIC_URL is required}"

exec select-ai a2a serve \
  --team "$A2A_TEAM" \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --public-url "$PUBLIC_URL"
