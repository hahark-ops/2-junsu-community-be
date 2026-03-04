#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-community-local}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl이 필요합니다."
  exit 1
fi

if kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
  kubectl delete namespace "${NAMESPACE}" --wait=true
  echo "[PASS] namespace 삭제 완료: ${NAMESPACE}"
else
  echo "namespace가 이미 없습니다: ${NAMESPACE}"
fi
