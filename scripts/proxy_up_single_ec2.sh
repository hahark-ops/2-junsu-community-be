#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.reverse-proxy.yml"
ENV_FILE="${1:-${ROOT_DIR}/deploy.proxy.env}"
HTTP_CONF="${ROOT_DIR}/docker/nginx/conf.d/default.conf"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "배포 env 파일이 없습니다: ${ENV_FILE}"
  echo "예시 생성:"
  echo "  cp ${ROOT_DIR}/deploy.proxy.env.example ${ROOT_DIR}/deploy.proxy.env"
  exit 1
fi

if [[ ! -f "${HTTP_CONF}" ]]; then
  echo "Nginx 기본 설정 파일이 없습니다: ${HTTP_CONF}"
  exit 1
fi

cd "${ROOT_DIR}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" pull
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --remove-orphans
./scripts/run_migrations.sh "${COMPOSE_FILE}" "${ENV_FILE}"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps

echo
echo "리버스 프록시 배포 완료"
echo "HTTP URL: http://<EC2_PUBLIC_IP>"
