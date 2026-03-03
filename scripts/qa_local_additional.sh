#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_COMPOSE="${ROOT_DIR}/docker-compose.reverse-proxy.yml"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/deploy.portainer.local.env}"

REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"
REGISTRY_USER="${REGISTRY_USER:-community}"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-community123!}"
PORTAINER_HTTPS_PORT="${PORTAINER_HTTPS_PORT:-9443}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"
EVIDENCE_DIR="${ROOT_DIR}/evidence/additional"

mkdir -p "${EVIDENCE_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[ERROR] env 파일이 없습니다: ${ENV_FILE}"
  echo "먼저 example을 복사하세요:"
  echo "  cp ${ROOT_DIR}/deploy.portainer.local.env.example ${ENV_FILE}"
  exit 1
fi

echo "[A] Portainer HTTPS 상태 확인"
PORTAINER_STATUS="$(curl -ksS -o "${EVIDENCE_DIR}/01-portainer-status.json" -w '%{http_code}' "https://localhost:${PORTAINER_HTTPS_PORT}/api/status" || true)"
if [[ "${PORTAINER_STATUS}" != "200" ]]; then
  echo "[FAIL] Portainer 상태 확인 실패(status=${PORTAINER_STATUS})"
  exit 1
fi

echo "[PASS] Portainer HTTPS status=200"

echo "[A] Registry 카탈로그 확인"
REGISTRY_STATUS="$(curl -sS -u "${REGISTRY_USER}:${REGISTRY_PASSWORD}" -o "${EVIDENCE_DIR}/02-registry-catalog.txt" -w '%{http_code}' "http://${REGISTRY_HOST}/v2/_catalog" || true)"
if [[ "${REGISTRY_STATUS}" != "200" ]]; then
  echo "[FAIL] Registry 카탈로그 확인 실패(status=${REGISTRY_STATUS})"
  exit 1
fi

echo "[PASS] Registry API status=200"

echo "[B] 앱 스택 실행"
docker compose --env-file "${ENV_FILE}" -f "${APP_COMPOSE}" up -d
"${ROOT_DIR}/scripts/run_migrations.sh" "${APP_COMPOSE}" "${ENV_FILE}"
docker compose --env-file "${ENV_FILE}" -f "${APP_COMPOSE}" ps | tee "${EVIDENCE_DIR}/04-compose-ps.txt"

echo "[C] 앱 헬스 체크"
curl -i --max-time 10 "${BASE_URL}/" | tee "${EVIDENCE_DIR}/05-health-root.txt"
curl -i --max-time 10 "${BASE_URL}/docs" | tee "${EVIDENCE_DIR}/06-health-docs.txt"

if [[ -n "${QA_EMAIL:-}" && -n "${QA_PASSWORD:-}" ]]; then
  echo "[C] 스모크 테스트 실행"
  QA_EMAIL="${QA_EMAIL}" QA_PASSWORD="${QA_PASSWORD}" QA_NICKNAME="${QA_NICKNAME:-awsai}" BASE_URL="${BASE_URL}" \
    "${ROOT_DIR}/scripts/qa_ec2_smoke.sh" | tee "${EVIDENCE_DIR}/07-smoke-result.txt"
else
  echo "[WARN] QA_EMAIL/QA_PASSWORD 미지정으로 스모크 테스트는 건너뜀"
fi

echo
cat <<EOF
[PASS] 추가 과제 로컬 QA 완료
- Portainer: https://localhost:${PORTAINER_HTTPS_PORT}
- Registry: http://${REGISTRY_HOST}
- Evidence: ${EVIDENCE_DIR}
EOF
