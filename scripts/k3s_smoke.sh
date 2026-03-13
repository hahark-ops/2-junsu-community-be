#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-${1:-}}"

if [[ -z "${BASE_URL}" ]]; then
  echo "사용법: BASE_URL=http://<public-ip> $0"
  exit 1
fi

if [[ -n "${QA_EMAIL:-}" && -n "${QA_PASSWORD:-}" ]]; then
  BASE_URL="${BASE_URL}" QA_EMAIL="${QA_EMAIL}" QA_PASSWORD="${QA_PASSWORD}" "${ROOT_DIR}/scripts/qa_ec2_smoke.sh"
  exit 0
fi

curl -fsS "${BASE_URL}/" >/dev/null
curl -fsS "${BASE_URL}/docs" >/dev/null
curl -fsS "${BASE_URL}/v1/posts" >/dev/null

echo "[PASS] 기본 k3s smoke 완료: ${BASE_URL}"

