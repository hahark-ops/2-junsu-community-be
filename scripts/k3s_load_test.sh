#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-${1:-}}"
OUT_FILE="${OUT_FILE:-/tmp/k3s-load-test-$(date +%Y%m%d-%H%M%S).txt}"

if [[ -z "${BASE_URL}" ]]; then
  echo "사용법: BASE_URL=http://<public-ip> $0"
  exit 1
fi

if ! command -v k6 >/dev/null 2>&1; then
  echo "k6 명령이 필요합니다."
  exit 1
fi

BASE_URL="${BASE_URL}" k6 run "${ROOT_DIR}/scripts/load/k6_public_smoke.js" | tee "${OUT_FILE}"

echo
echo "[PASS] k6 부하 테스트 완료"
echo "결과 파일: ${OUT_FILE}"

