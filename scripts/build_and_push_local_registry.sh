#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_FE_DIR="${ROOT_DIR}/../2-junsu-community-fe"
FE_DIR="${FE_DIR:-${DEFAULT_FE_DIR}}"

REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"
REGISTRY_USER="${REGISTRY_USER:-community}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-community123!}"
TAG="${TAG:-local}"
PLATFORM="${PLATFORM:-linux/amd64}"
EVIDENCE_DIR="${ROOT_DIR}/evidence/additional"

BE_IMAGE="${REGISTRY_HOST}/community-be:${TAG}"
FE_IMAGE="${REGISTRY_HOST}/community-fe:${TAG}"
DB_IMAGE="${REGISTRY_HOST}/community-db:${TAG}"

if [[ ! -d "${FE_DIR}" ]]; then
  echo "[ERROR] FE_DIR 경로를 찾지 못했습니다: ${FE_DIR}"
  echo "예: FE_DIR=/Users/junsu/Desktop/2-junsu-community-fe $0"
  exit 1
fi

if [[ ! -f "${FE_DIR}/Dockerfile" ]]; then
  echo "[ERROR] FE Dockerfile을 찾을 수 없습니다: ${FE_DIR}/Dockerfile"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker 데몬에 연결할 수 없습니다."
  exit 1
fi

mkdir -p "${EVIDENCE_DIR}"

echo "[INFO] Registry 로그인: ${REGISTRY_HOST}"
if ! echo "${REGISTRY_PASSWORD}" | docker login "${REGISTRY_HOST}" -u "${REGISTRY_USER}" --password-stdin; then
  cat <<EOF
[ERROR] 레지스트리 로그인 실패.
- docker-compose.portainer.yml의 registry가 실행 중인지 확인하세요.
- Docker Desktop에서 insecure registry 설정이 필요할 수 있습니다.
  예) Settings -> Docker Engine -> "insecure-registries": ["${REGISTRY_HOST}"]
EOF
  exit 1
fi

echo "[INFO] 이미지 빌드"
docker build --platform "${PLATFORM}" -t "${BE_IMAGE}" -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"
docker build --platform "${PLATFORM}" -t "${FE_IMAGE}" -f "${FE_DIR}/Dockerfile" "${FE_DIR}"
docker build --platform "${PLATFORM}" -t "${DB_IMAGE}" -f "${ROOT_DIR}/docker/db.Dockerfile" "${ROOT_DIR}"

echo "[INFO] 이미지 푸시"
{
  docker push "${BE_IMAGE}"
  docker push "${FE_IMAGE}"
  docker push "${DB_IMAGE}"
} | tee "${EVIDENCE_DIR}/03-push-log.txt"

echo "[INFO] 레지스트리 카탈로그 확인"
curl -sS -u "${REGISTRY_USER}:${REGISTRY_PASSWORD}" "http://${REGISTRY_HOST}/v2/_catalog" || true

echo
cat <<EOF
[PASS] 로컬 private registry 푸시 완료
- ${BE_IMAGE}
- ${FE_IMAGE}
- ${DB_IMAGE}
EOF
