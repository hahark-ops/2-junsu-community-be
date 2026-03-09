#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="${ROOT_DIR}/k8s"
NAMESPACE="${NAMESPACE:-community-local}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-30080}"
PORT_FORWARD_HOST="${PORT_FORWARD_HOST:-127.0.0.1}"
PORT_FORWARD_PID_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.pid"
PORT_FORWARD_LOG_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.log"

BE_IMAGE="${BE_IMAGE:-community-be:local}"
FE_IMAGE="${FE_IMAGE:-community-fe:local}"
DB_IMAGE="${DB_IMAGE:-community-db:local}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 명령이 필요합니다."
    exit 1
  fi
}

ensure_image_exists() {
  local source_image="$1"
  local target_image="$2"
  local fallback_image="$3"

  if docker image inspect "${target_image}" >/dev/null 2>&1; then
    return 0
  fi

  if docker image inspect "${source_image}" >/dev/null 2>&1; then
    echo "[INFO] 이미지 태그 변환: ${source_image} -> ${target_image}"
    docker tag "${source_image}" "${target_image}"
    return 0
  fi

  if docker image inspect "${fallback_image}" >/dev/null 2>&1; then
    echo "[INFO] 이미지 태그 변환: ${fallback_image} -> ${target_image}"
    docker tag "${fallback_image}" "${target_image}"
    return 0
  fi

  echo "[ERROR] 로컬 이미지가 없습니다: ${target_image}"
  echo "        확인한 태그: ${source_image}, ${fallback_image}"
  exit 1
}

start_port_forward() {
  if [[ -f "${PORT_FORWARD_PID_FILE}" ]]; then
    local existing_pid
    existing_pid="$(cat "${PORT_FORWARD_PID_FILE}")"
    if kill -0 "${existing_pid}" >/dev/null 2>&1; then
      return 0
    fi
    rm -f "${PORT_FORWARD_PID_FILE}"
  fi

  : > "${PORT_FORWARD_LOG_FILE}"
  kubectl -n "${NAMESPACE}" port-forward svc/community-nginx "${PORT_FORWARD_PORT}:80" >"${PORT_FORWARD_LOG_FILE}" 2>&1 &
  echo $! > "${PORT_FORWARD_PID_FILE}"

  for _ in $(seq 1 30); do
    if curl -fsS "http://${PORT_FORWARD_HOST}:${PORT_FORWARD_PORT}/login.html" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "[ERROR] port-forward 준비 실패: http://${PORT_FORWARD_HOST}:${PORT_FORWARD_PORT}"
  echo "--- port-forward log ---"
  cat "${PORT_FORWARD_LOG_FILE}" || true
  exit 1
}

require_cmd kubectl
require_cmd docker
require_cmd curl

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "Kubernetes 클러스터에 연결할 수 없습니다. Docker Desktop > Kubernetes를 확인하세요."
  exit 1
fi

if [[ ! -f "${K8S_DIR}/kustomization.yaml" || ! -f "${K8S_DIR}/community-workloads.yaml" ]]; then
  echo "k8s 매니페스트를 찾을 수 없습니다."
  exit 1
fi

ensure_image_exists "${BE_IMAGE}" "community-be:local" "localhost:5001/community-be:local"
ensure_image_exists "${FE_IMAGE}" "community-fe:local" "localhost:5001/community-fe:local"
ensure_image_exists "${DB_IMAGE}" "community-db:local" "localhost:5001/community-db:local"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
cp -R "${K8S_DIR}/." "${TMP_DIR}/"

python3 - "$TMP_DIR" "$NAMESPACE" <<'PY'
from pathlib import Path
import sys

tmp_dir = Path(sys.argv[1])
namespace = sys.argv[2]
kustomization = tmp_dir / "kustomization.yaml"
content = kustomization.read_text(encoding="utf-8")
content = content.replace("namespace: community-local", f"namespace: {namespace}")
kustomization.write_text(content, encoding="utf-8")
PY

kubectl apply -k "${TMP_DIR}"

kubectl -n "${NAMESPACE}" rollout status deploy/community-db --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-be --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-fe --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-nginx --timeout=240s

start_port_forward

echo
printf '[PASS] Kubernetes 로컬 배포 완료\n'
printf 'Namespace : %s\n' "${NAMESPACE}"
printf 'App URL   : http://%s:%s\n' "${PORT_FORWARD_HOST}" "${PORT_FORWARD_PORT}"
printf 'Docs URL  : http://%s:%s/docs\n' "${PORT_FORWARD_HOST}" "${PORT_FORWARD_PORT}"
printf 'Forward   : svc/community-nginx -> %s:80\n' "${PORT_FORWARD_PORT}"
echo
printf '스모크 테스트:\n'
printf "QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' PORT_FORWARD_PORT='%s' %s/scripts/k8s_qa_local.sh\n" "${PORT_FORWARD_PORT}" "${ROOT_DIR}"
