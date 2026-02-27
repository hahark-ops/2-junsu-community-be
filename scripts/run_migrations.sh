#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${1:-${ROOT_DIR}/docker-compose.yml}"
ENV_FILE="${2:-}"
MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260226_add_session_expiry.sql"
SCHEMA_FILE="${ROOT_DIR}/schema.sql"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose 파일이 없습니다: ${COMPOSE_FILE}"
  exit 1
fi

if [[ ! -f "${MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${SCHEMA_FILE}" ]]; then
  echo "스키마 파일이 없습니다: ${SCHEMA_FILE}"
  exit 1
fi

if [[ -n "${ENV_FILE}" && ! -f "${ENV_FILE}" ]]; then
  echo "env 파일이 없습니다: ${ENV_FILE}"
  exit 1
fi

compose_exec() {
  if [[ -n "${ENV_FILE}" ]] && docker compose --help 2>/dev/null | grep -q -- '--env-file'; then
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
    return
  fi

  if [[ -n "${ENV_FILE}" ]]; then
    (
      set -a
      # shellcheck disable=SC1090
      source "${ENV_FILE}"
      set +a
      docker compose -f "${COMPOSE_FILE}" "$@"
    )
    return
  fi

  docker compose -f "${COMPOSE_FILE}" "$@"
}

echo "DB 준비 상태 확인 중..."
db_ready=0
for _ in {1..30}; do
  if compose_exec exec -T db sh -lc 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent' >/dev/null 2>&1; then
    db_ready=1
    break
  fi
  sleep 2
done

if [[ "${db_ready}" -ne 1 ]]; then
  echo "DB가 준비되지 않아 마이그레이션을 적용할 수 없습니다."
  exit 1
fi

db_name="$(compose_exec exec -T db sh -lc 'printf "%s" "${MYSQL_DATABASE:-}"')"
if [[ -z "${db_name}" ]]; then
  echo "MYSQL_DATABASE 값이 비어 있어 마이그레이션을 적용할 수 없습니다."
  exit 1
fi

status="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT
  (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''sessions'\''),
  (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''sessions'\'' AND COLUMN_NAME = '\''expiresAt'\''),
  (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''sessions'\'' AND COLUMN_NAME = '\''expiresAt'\'' AND IS_NULLABLE = '\''NO'\''),
  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''sessions'\'' AND INDEX_NAME = '\''idx_sessions_expiresAt'\'')
"
')"

IFS=$'\t' read -r sessions_table_exists expires_column_exists expires_not_null_exists expires_index_exists <<< "${status}"

if [[ "${sessions_table_exists:-0}" -eq 0 ]]; then
  echo "sessions 테이블이 없어 schema.sql을 먼저 적용합니다..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${SCHEMA_FILE}"
  echo "스키마 적용 완료: $(basename "${SCHEMA_FILE}")"
  sessions_table_exists=1
  expires_column_exists=1
  expires_not_null_exists=1
  expires_index_exists=1
fi

if [[ "${expires_column_exists:-0}" -eq 1 && "${expires_not_null_exists:-0}" -eq 1 && "${expires_index_exists:-0}" -eq 1 ]]; then
  echo "세션 만료 스키마가 이미 반영되어 있어 마이그레이션을 건너뜁니다."
  exit 0
fi

echo "세션 만료 마이그레이션 적용 중..."
compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${MIGRATION_FILE}"
echo "마이그레이션 적용 완료: $(basename "${MIGRATION_FILE}")"
