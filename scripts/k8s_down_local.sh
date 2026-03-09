#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-community-local}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-30080}"
PORT_FORWARD_PID_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.pid"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl이 필요합니다."
  exit 1
fi

if [[ -f "${PORT_FORWARD_PID_FILE}" ]]; then
  PORT_FORWARD_PID="$(cat "${PORT_FORWARD_PID_FILE}")"
  kill "${PORT_FORWARD_PID}" >/dev/null 2>&1 || true
  rm -f "${PORT_FORWARD_PID_FILE}"
fi

if kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
  kubectl delete namespace "${NAMESPACE}" --wait=true
  echo "[PASS] namespace 삭제 완료: ${NAMESPACE}"
else
  echo "namespace가 이미 없습니다: ${NAMESPACE}"
fi
