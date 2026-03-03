#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.portainer.yml"
LOCAL_DIR="${ROOT_DIR}/local/portainer"
CERT_DIR="${LOCAL_DIR}/certs"
AUTH_DIR="${LOCAL_DIR}/auth"

REGISTRY_USER="${REGISTRY_USER:-community}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-community123!}"
FORCE_REGEN_CERT="${FORCE_REGEN_CERT:-false}"
REGISTRY_PORT="${REGISTRY_PORT:-5000}"
PORTAINER_HTTPS_PORT="${PORTAINER_HTTPS_PORT:-9443}"
REGISTRY_HOST="${REGISTRY_HOST:-localhost:${REGISTRY_PORT}}"
PORTAINER_URL="${PORTAINER_URL:-https://localhost:${PORTAINER_HTTPS_PORT}}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker 명령을 찾을 수 없습니다. Docker Desktop(또는 Docker Engine)을 먼저 설치하세요."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker 데몬에 연결할 수 없습니다. Docker Desktop을 실행한 뒤 다시 시도하세요."
  exit 1
fi

if ! command -v mkcert >/dev/null 2>&1; then
  cat <<'EOF'
[ERROR] mkcert가 설치되어 있지 않습니다.
macOS(Homebrew) 기준 설치:
  brew install mkcert nss
  mkcert -install
EOF
  exit 1
fi

mkdir -p "${CERT_DIR}" "${AUTH_DIR}"

if [[ "${FORCE_REGEN_CERT}" == "true" || ! -f "${CERT_DIR}/portainer.crt" || ! -f "${CERT_DIR}/portainer.key" ]]; then
  echo "[INFO] 로컬 신뢰 인증서 생성 (localhost, 127.0.0.1)"
  mkcert -install >/dev/null 2>&1 || true
  mkcert \
    -cert-file "${CERT_DIR}/portainer.crt" \
    -key-file "${CERT_DIR}/portainer.key" \
    localhost 127.0.0.1 ::1
else
  echo "[INFO] 기존 인증서 재사용: ${CERT_DIR}/portainer.crt"
fi

echo "[INFO] Registry htpasswd 생성"
docker run --rm --entrypoint htpasswd httpd:2.4-alpine -Bbn "${REGISTRY_USER}" "${REGISTRY_PASSWORD}" > "${AUTH_DIR}/htpasswd"

echo "[INFO] Portainer + Registry 스택 기동"
docker compose -f "${COMPOSE_FILE}" up -d

PORTAINER_STATUS="$(curl -ksS -o /tmp/portainer-status.json -w '%{http_code}' "${PORTAINER_URL}/api/status" || true)"
REGISTRY_STATUS="$(curl -sS -u "${REGISTRY_USER}:${REGISTRY_PASSWORD}" -o /tmp/registry-catalog.json -w '%{http_code}' "http://${REGISTRY_HOST}/v2/_catalog" || true)"

echo
if [[ "${PORTAINER_STATUS}" == "200" ]]; then
  echo "[PASS] Portainer HTTPS: ${PORTAINER_URL}"
else
  echo "[WARN] Portainer 상태 확인 실패(status=${PORTAINER_STATUS}). 컨테이너 로그를 확인하세요."
fi

if [[ "${REGISTRY_STATUS}" == "200" ]]; then
  echo "[PASS] Registry API: http://${REGISTRY_HOST}/v2/_catalog"
else
  echo "[WARN] Registry 카탈로그 확인 실패(status=${REGISTRY_STATUS})."
fi

echo
cat <<EOF
다음 단계:
1) 이미지 빌드/푸시
   REGISTRY_HOST='${REGISTRY_HOST}' REGISTRY_USER='${REGISTRY_USER}' REGISTRY_PASSWORD='***' ${ROOT_DIR}/scripts/build_and_push_local_registry.sh
2) 앱 스택 실행
   cp ${ROOT_DIR}/deploy.portainer.local.env.example ${ROOT_DIR}/deploy.portainer.local.env
   docker compose --env-file ${ROOT_DIR}/deploy.portainer.local.env -f ${ROOT_DIR}/docker-compose.reverse-proxy.yml up -d
EOF
