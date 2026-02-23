#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <analytics_api_route_url>"
  echo "Example: $0 https://xxxx.execute-api.ap-northeast-2.amazonaws.com/v1/analytics/health"
  exit 1
fi

ANALYTICS_API_URL="$1"
RESP_FILE="$(mktemp)"
trap 'rm -f "${RESP_FILE}"' EXIT

HTTP_CODE="$(curl -sS -o "${RESP_FILE}" -w "%{http_code}" "${ANALYTICS_API_URL}")"

echo "status=${HTTP_CODE}"
cat "${RESP_FILE}"
echo

if [[ "${HTTP_CODE}" != "200" ]]; then
  echo "Athena 경로 검증 실패"
  exit 1
fi

echo "Athena 경로 검증 성공 (API Gateway -> Lambda -> Athena)"
