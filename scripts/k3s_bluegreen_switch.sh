#!/usr/bin/env bash
set -euo pipefail

TARGET_COLOR="${1:-}"
NAMESPACE="${NAMESPACE:-community-k3s}"

if [[ "${TARGET_COLOR}" != "blue" && "${TARGET_COLOR}" != "green" ]]; then
  echo "사용법: $0 <blue|green>"
  exit 1
fi

kubectl -n "${NAMESPACE}" patch service community-be --type merge -p "{\"spec\":{\"selector\":{\"app\":\"community-be\",\"active\":\"${TARGET_COLOR}\"}}}"
kubectl -n "${NAMESPACE}" patch service community-fe --type merge -p "{\"spec\":{\"selector\":{\"app\":\"community-fe\",\"active\":\"${TARGET_COLOR}\"}}}"

echo "[PASS] blue/green active color 전환 완료: ${TARGET_COLOR}"

