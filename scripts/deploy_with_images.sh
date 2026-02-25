#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/deploy.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "배포 env 파일이 없습니다: ${ENV_FILE}"
  echo "예시 생성: cp ${ROOT_DIR}/deploy.env.example ${ROOT_DIR}/deploy.env"
  exit 1
fi

cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml pull
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml up -d
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml ps
