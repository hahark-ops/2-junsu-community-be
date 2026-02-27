#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <be_lambda_api_endpoint>"
  echo "Example: $0 https://abcd1234.execute-api.ap-northeast-2.amazonaws.com"
  exit 1
fi

BASE="${1%/}"
BODY_FILE="$(mktemp)"
trap 'rm -f "${BODY_FILE}"' EXIT

request_with_retry() {
  local path="$1"
  local expected_regex="$2"
  local label="$3"
  local status=""

  for attempt in {1..6}; do
    status="$(curl -sS -o "${BODY_FILE}" -w "%{http_code}" --max-time 20 "${BASE}${path}" || true)"
    if [[ "${status}" =~ ^(${expected_regex})$ ]]; then
      echo "[PASS] ${label} (status=${status}, attempt=${attempt})"
      sed -n '1,20p' "${BODY_FILE}"
      echo
      return 0
    fi

    echo "[INFO] ${label} not ready (status=${status:-curl_error}, attempt=${attempt}/6)"
    sleep 5
  done

  echo "[FAIL] ${label}: expected ${expected_regex}, got ${status:-curl_error}"
  sed -n '1,40p' "${BODY_FILE}" || true
  exit 1
}

echo "[1] health"
request_with_retry "/" "200" "health"

echo "[2] docs"
request_with_retry "/docs" "200" "docs"

echo "[3] protected api (expect 401)"
request_with_retry "/v1/auth/me" "401" "auth/me unauthorized"
