#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="${ROOT_DIR}/k8s"
NAMESPACE="${NAMESPACE:-community-local}"
K8S_TARGET="${K8S_TARGET:-base}"
PORT_FORWARD_PORT="${PORT_FORWARD_PORT:-30080}"
PORT_FORWARD_HOST="${PORT_FORWARD_HOST:-127.0.0.1}"
PORT_FORWARD_PID_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.pid"
PORT_FORWARD_LOG_FILE="/tmp/community-k8s-port-forward-${NAMESPACE}-${PORT_FORWARD_PORT}.log"

BE_IMAGE="${BE_IMAGE:-community-be:local}"
FE_IMAGE="${FE_IMAGE:-community-fe:local}"
DB_IMAGE="${DB_IMAGE:-community-db:local}"
DB_SECRET_ENV="${K8S_DIR}/base/config/db-secrets.env"
DB_SECRET_ENV_EXAMPLE="${K8S_DIR}/base/config/db-secrets.env.example"
APP_SECRET_ENV="${K8S_DIR}/base/config/app-secrets.env"
APP_SECRET_ENV_EXAMPLE="${K8S_DIR}/base/config/app-secrets.env.example"

case "${K8S_TARGET}" in
  base)
    KUSTOMIZE_PATH="${K8S_DIR}/base"
    ;;
  dm-scale-proof)
    KUSTOMIZE_PATH="${K8S_DIR}/overlays/dm-scale-proof"
    ;;
  *)
    echo "[ERROR] 지원하지 않는 K8S_TARGET입니다: ${K8S_TARGET}"
    echo "        사용 가능 값: base, dm-scale-proof"
    exit 1
    ;;
esac

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

ensure_secret_env_file() {
  local target_file="$1"
  local example_file="$2"
  local file_label="$3"

  if [[ ! -f "${example_file}" ]]; then
    echo "[ERROR] 예시 secret 파일이 없습니다: ${example_file}"
    exit 1
  fi

  if [[ ! -f "${target_file}" ]]; then
    cp "${example_file}" "${target_file}"
    echo "[ERROR] ${file_label} 파일이 없어 예시 파일을 생성했습니다: ${target_file}"
    echo "        값을 수정한 뒤 다시 실행하세요."
    exit 1
  fi

  if grep -Eqi 'change_me_|example_|replace_me_' "${target_file}"; then
    echo "[ERROR] ${file_label}에 placeholder 값이 남아 있습니다: ${target_file}"
    echo "        example 값을 실제 로컬 값으로 수정한 뒤 다시 실행하세요."
    exit 1
  fi
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

if [[ ! -d "${KUSTOMIZE_PATH}" ]]; then
  echo "[ERROR] Kustomize 경로를 찾을 수 없습니다: ${KUSTOMIZE_PATH}"
  exit 1
fi

ensure_secret_env_file "${DB_SECRET_ENV}" "${DB_SECRET_ENV_EXAMPLE}" "DB secret"
ensure_secret_env_file "${APP_SECRET_ENV}" "${APP_SECRET_ENV_EXAMPLE}" "App secret"

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "Kubernetes 클러스터에 연결할 수 없습니다. Docker Desktop > Kubernetes를 확인하세요."
  exit 1
fi

ensure_image_exists "${BE_IMAGE}" "community-be:local" "localhost:5001/community-be:local"
ensure_image_exists "${FE_IMAGE}" "community-fe:local" "localhost:5001/community-fe:local"
ensure_image_exists "${DB_IMAGE}" "community-db:local" "localhost:5001/community-db:local"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" delete job community-be-migrate --ignore-not-found --wait=true >/dev/null 2>&1 || true
kubectl apply -k "${KUSTOMIZE_PATH}" --namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" rollout status deploy/community-db --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-redis --timeout=240s

kubectl -n "${NAMESPACE}" wait --for=condition=complete job/community-be-migrate --timeout=240s

kubectl -n "${NAMESPACE}" rollout status deploy/community-be --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-fe --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-nginx --timeout=240s

start_port_forward

echo
printf '[PASS] Kubernetes 로컬 배포 완료\n'
printf 'Target    : %s\n' "${K8S_TARGET}"
printf 'Namespace : %s\n' "${NAMESPACE}"
printf 'App URL   : http://%s:%s\n' "${PORT_FORWARD_HOST}" "${PORT_FORWARD_PORT}"
printf 'Docs URL  : http://%s:%s/docs\n' "${PORT_FORWARD_HOST}" "${PORT_FORWARD_PORT}"
printf 'Forward   : svc/community-nginx -> %s:80\n' "${PORT_FORWARD_PORT}"
echo
printf '스모크 테스트:\n'
printf "QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' PORT_FORWARD_PORT='%s' %s/scripts/k8s_qa_local.sh\n" "${PORT_FORWARD_PORT}" "${ROOT_DIR}"
