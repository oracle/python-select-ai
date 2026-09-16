#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

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

: "${PUBLIC_URL:?PUBLIC_URL is required}"
: "${SELECT_AI_POOL_MAX_SIZE:=10}"

serve_args=(
  --deployment standalone
  --host 0.0.0.0
  --port "${PORT:-8080}"
  --pool-max-size "$SELECT_AI_POOL_MAX_SIZE"
  --public-url "$PUBLIC_URL"
)
if [ -n "${SELECT_AI_A2A_TEAM:-}" ]; then
  serve_args+=(--team "$SELECT_AI_A2A_TEAM")
fi
if [ "${SELECT_AI_A2A_REQUIRE_OAUTH:-false}" = "true" ]; then
  serve_args+=(--require-oauth)
fi

exec select-ai a2a serve "${serve_args[@]}"
