#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${1:-${ROOT_DIR}/docker-compose.yml}"
ENV_FILE="${2:-}"
MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260226_add_session_expiry.sql"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose 파일이 없습니다: ${COMPOSE_FILE}"
  exit 1
fi

if [[ ! -f "${MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${MIGRATION_FILE}"
  exit 1
fi

compose_cmd=(docker compose)
if [[ -n "${ENV_FILE}" ]]; then
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "env 파일이 없습니다: ${ENV_FILE}"
    exit 1
  fi
  compose_cmd+=(--env-file "${ENV_FILE}")
fi
compose_cmd+=(-f "${COMPOSE_FILE}")

echo "DB 준비 상태 확인 중..."
db_ready=0
for _ in {1..30}; do
  if "${compose_cmd[@]}" exec -T db sh -lc 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent' >/dev/null 2>&1; then
    db_ready=1
    break
  fi
  sleep 2
done

if [[ "${db_ready}" -ne 1 ]]; then
  echo "DB가 준비되지 않아 마이그레이션을 적용할 수 없습니다."
  exit 1
fi

echo "세션 만료 마이그레이션 적용 중..."
"${compose_cmd[@]}" exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${MIGRATION_FILE}"
echo "마이그레이션 적용 완료: $(basename "${MIGRATION_FILE}")"
