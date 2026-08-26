#!/usr/bin/env sh

# Cloud Run-only A2A launcher. It expands the optional wallet archive mounted
# by deploy.sh, then starts the generic select-ai CLI in A2A server mode.

set -eu

wallet_archive=/var/run/secrets/select-ai-wallet/wallet.zip
wallet_root=/tmp/select-ai-wallet

if [ -f "$wallet_archive" ]; then
  mkdir -p "$wallet_root"
  chmod 700 "$wallet_root"
  unzip -q "$wallet_archive" -d "$wallet_root"

  wallet_file="$(find "$wallet_root" -type f -name ewallet.pem -print -quit)"
  if [ -z "$wallet_file" ]; then
    echo "Wallet ZIP does not contain ewallet.pem" >&2
    exit 1
  fi
  export SELECT_AI_WALLET_LOCATION="$(dirname "$wallet_file")"
fi

: "${SELECT_AI_A2A_TEAM:?SELECT_AI_A2A_TEAM is required}"
: "${PUBLIC_URL:?PUBLIC_URL is required}"
: "${SELECT_AI_POOL_MAX_SIZE:=10}"

exec select-ai a2a serve \
  --team "$SELECT_AI_A2A_TEAM" \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --pool-max-size "$SELECT_AI_POOL_MAX_SIZE" \
  --public-url "$PUBLIC_URL"
