#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-community-local}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-30080}"
PORT_FORWARD_HOST="${PORT_FORWARD_HOST:-127.0.0.1}"
PORT_FORWARD_PID_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.pid"
PORT_FORWARD_LOG_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.log"
BASE_URL="${BASE_URL:-http://${PORT_FORWARD_HOST}:${PORT_FORWARD_PORT}}"
QA_EMAIL="${QA_EMAIL:-qa-local@example.com}"
QA_PASSWORD="${QA_PASSWORD:-Wrong1!A}"
QA_NICKNAME="${QA_NICKNAME:-k8sqa}"
STARTED_FORWARD=0

cleanup() {
  if [[ "${STARTED_FORWARD}" == "1" && -f "${PORT_FORWARD_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${PORT_FORWARD_PID_FILE}")"
    kill "${pid}" >/dev/null 2>&1 || true
    rm -f "${PORT_FORWARD_PID_FILE}"
  fi
}
trap cleanup EXIT

ensure_port_forward() {
  if curl -fsS "${BASE_URL}/login.html" >/dev/null 2>&1; then
    return 0
  fi

  if [[ -f "${PORT_FORWARD_PID_FILE}" ]]; then
    local existing_pid
    existing_pid="$(cat "${PORT_FORWARD_PID_FILE}")"
    if ! kill -0 "${existing_pid}" >/dev/null 2>&1; then
      rm -f "${PORT_FORWARD_PID_FILE}"
    fi
  fi

  if [[ ! -f "${PORT_FORWARD_PID_FILE}" ]]; then
    kubectl -n "${NAMESPACE}" port-forward svc/community-nginx "${PORT_FORWARD_PORT}:80" >"${PORT_FORWARD_LOG_FILE}" 2>&1 &
    echo $! > "${PORT_FORWARD_PID_FILE}"
    STARTED_FORWARD=1
  fi

  for _ in $(seq 1 20); do
    if curl -fsS "${BASE_URL}/login.html" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "[ERROR] K8s 앱 접근 실패: ${BASE_URL}"
  [[ -f "${PORT_FORWARD_LOG_FILE}" ]] && cat "${PORT_FORWARD_LOG_FILE}" || true
  exit 1
}

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl이 필요합니다."
  exit 1
fi

if ! kubectl -n "${NAMESPACE}" get svc community-nginx >/dev/null 2>&1; then
  echo "community-nginx 서비스가 없습니다. 먼저 ./scripts/k8s_up_local.sh 를 실행하세요."
  exit 1
fi

ensure_port_forward

QA_EMAIL="${QA_EMAIL}" \
QA_PASSWORD="${QA_PASSWORD}" \
QA_NICKNAME="${QA_NICKNAME}" \
BASE_URL="${BASE_URL}" \
"${ROOT_DIR}/scripts/qa_ec2_smoke.sh"
