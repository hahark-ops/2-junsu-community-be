#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <be_lambda_api_endpoint>"
  echo "Example: $0 https://abcd1234.execute-api.ap-northeast-2.amazonaws.com"
  exit 1
fi

BASE="${1%/}"

echo "[1] health"
curl -i --max-time 10 "${BASE}/" | sed -n '1,20p'
echo

echo "[2] docs"
curl -i --max-time 10 "${BASE}/docs" | sed -n '1,20p'
echo

echo "[3] protected api (expect 401)"
curl -i --max-time 10 "${BASE}/v1/auth/me" | sed -n '1,20p'
echo
