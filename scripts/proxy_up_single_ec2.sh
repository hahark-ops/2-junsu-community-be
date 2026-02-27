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

# AMI별로 docker compose 플러그인/standalone(docker-compose) 차이를 흡수.
if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=(docker-compose)
else
  echo "docker compose 또는 docker-compose를 찾을 수 없습니다."
  exit 1
fi

compose_cmd() {
  if "${COMPOSE_BIN[@]}" --help 2>/dev/null | grep -q -- '--env-file'; then
    "${COMPOSE_BIN[@]}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
    return
  fi

  (
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
    "${COMPOSE_BIN[@]}" -f "${COMPOSE_FILE}" "$@"
  )
}

# 이전 수동 실행/타 경로 compose 잔존 컨테이너 이름 충돌 방지
for container in community-db community-be community-fe community-nginx; do
  docker rm -f "${container}" >/dev/null 2>&1 || true
done

compose_cmd pull
compose_cmd up -d --remove-orphans
./scripts/run_migrations.sh "${COMPOSE_FILE}" "${ENV_FILE}"
compose_cmd ps

echo
echo "리버스 프록시 배포 완료"
echo "HTTP URL: http://<EC2_PUBLIC_IP>"
