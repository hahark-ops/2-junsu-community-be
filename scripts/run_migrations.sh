#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${1:-${ROOT_DIR}/docker-compose.yml}"
ENV_FILE="${2:-}"
MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260226_add_session_expiry.sql"
LIKE_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260309_ensure_like_unique.sql"
DM_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260309_add_dm_tables.sql"
DM_READ_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260309_add_dm_room_reads.sql"
DM_CLIENT_MESSAGE_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260312_add_dm_client_message_id.sql"
DM_REALTIME_PUBLISHED_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260312_add_dm_realtime_published.sql"
WEB_PUSH_SUBSCRIPTIONS_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260312_add_web_push_subscriptions.sql"
WEB_PUSH_ENDPOINT_HASH_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260312_fix_web_push_endpoint_hash.sql"
HARD_DELETE_MIGRATION_FILE="${ROOT_DIR}/scripts/migrations/20260312_drop_users_is_deleted.sql"
SCHEMA_FILE="${ROOT_DIR}/schema.sql"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose 파일이 없습니다: ${COMPOSE_FILE}"
  exit 1
fi

if [[ ! -f "${MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${LIKE_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${LIKE_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${DM_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${DM_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${DM_READ_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${DM_READ_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${DM_CLIENT_MESSAGE_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${DM_CLIENT_MESSAGE_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${DM_REALTIME_PUBLISHED_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${DM_REALTIME_PUBLISHED_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${WEB_PUSH_SUBSCRIPTIONS_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${WEB_PUSH_SUBSCRIPTIONS_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${WEB_PUSH_ENDPOINT_HASH_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${WEB_PUSH_ENDPOINT_HASH_MIGRATION_FILE}"
  exit 1
fi

if [[ ! -f "${HARD_DELETE_MIGRATION_FILE}" ]]; then
  echo "마이그레이션 파일이 없습니다: ${HARD_DELETE_MIGRATION_FILE}"
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

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=(docker-compose)
else
  echo "docker compose 또는 docker-compose를 찾을 수 없습니다."
  exit 1
fi

compose_exec() {
  if [[ -n "${ENV_FILE}" ]] && "${COMPOSE_BIN[@]}" --help 2>/dev/null | grep -q -- '--env-file'; then
    "${COMPOSE_BIN[@]}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
    return
  fi

  if [[ -n "${ENV_FILE}" ]]; then
    (
      set -a
      # shellcheck disable=SC1090
      source "${ENV_FILE}"
      set +a
      "${COMPOSE_BIN[@]}" -f "${COMPOSE_FILE}" "$@"
    )
    return
  fi

  "${COMPOSE_BIN[@]}" -f "${COMPOSE_FILE}" "$@"
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
else
  echo "세션 만료 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${MIGRATION_FILE}")"
fi

like_unique_exists="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT COUNT(*)
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '\''likes'\''
  AND INDEX_NAME = '\''unique_like'\''
"
')"

if [[ "${like_unique_exists:-0}" -eq 0 ]]; then
  echo "좋아요 유니크 제약 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${LIKE_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${LIKE_MIGRATION_FILE}")"
else
  echo "좋아요 유니크 제약이 이미 반영되어 있어 마이그레이션을 건너뜁니다."
fi

dm_tables_status="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT
  (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''dm_rooms'\''),
  (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''dm_messages'\'')
"
')"

IFS=$'\t' read -r dm_rooms_exists dm_messages_exists <<< "${dm_tables_status}"

if [[ "${dm_rooms_exists:-0}" -eq 1 && "${dm_messages_exists:-0}" -eq 1 ]]; then
  echo "DM 테이블이 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "DM 테이블 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${DM_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${DM_MIGRATION_FILE}")"
fi

dm_reads_exists="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '\''dm_room_reads'\''
"
')"

if [[ "${dm_reads_exists:-0}" -eq 1 ]]; then
  echo "DM 읽음 상태 테이블이 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "DM 읽음 상태 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${DM_READ_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${DM_READ_MIGRATION_FILE}")"
fi

dm_client_message_status="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT
  (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''dm_messages'\'' AND COLUMN_NAME = '\''clientMessageId'\''),
  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''dm_messages'\'' AND INDEX_NAME = '\''unique_dm_message_client'\'')
"
')"

IFS=$'\t' read -r dm_client_message_column_exists dm_client_message_unique_exists <<< "${dm_client_message_status}"

if [[ "${dm_client_message_column_exists:-0}" -eq 1 && "${dm_client_message_unique_exists:-0}" -eq 1 ]]; then
  echo "DM clientMessageId 스키마가 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "DM clientMessageId 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${DM_CLIENT_MESSAGE_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${DM_CLIENT_MESSAGE_MIGRATION_FILE}")"
fi

dm_realtime_published_exists="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '\''dm_messages'\''
  AND COLUMN_NAME = '\''realtimePublishedAt'\''
"
')"

if [[ "${dm_realtime_published_exists:-0}" -eq 1 ]]; then
  echo "DM realtimePublishedAt 스키마가 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "DM realtimePublishedAt 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${DM_REALTIME_PUBLISHED_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${DM_REALTIME_PUBLISHED_MIGRATION_FILE}")"
fi

users_is_deleted_exists="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT COUNT(*)
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '\''users'\''
  AND COLUMN_NAME = '\''is_deleted'\''
"
')"

if [[ "${users_is_deleted_exists:-0}" -eq 1 ]]; then
  echo "회원 hard delete 스키마 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${HARD_DELETE_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${HARD_DELETE_MIGRATION_FILE}")"
else
  echo "회원 hard delete 스키마가 이미 반영되어 있어 마이그레이션을 건너뜁니다."
fi

web_push_subscriptions_exists="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = '\''web_push_subscriptions'\''
"
')"

if [[ "${web_push_subscriptions_exists:-0}" -eq 1 ]]; then
  echo "웹푸시 구독 테이블이 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "웹푸시 구독 테이블 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${WEB_PUSH_SUBSCRIPTIONS_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${WEB_PUSH_SUBSCRIPTIONS_MIGRATION_FILE}")"
fi

web_push_endpoint_hash_status="$(compose_exec exec -T db sh -lc '
mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "
SELECT
  (SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''web_push_subscriptions'\'' AND COLUMN_NAME = '\''endpointHash'\''),
  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\''web_push_subscriptions'\'' AND INDEX_NAME = '\''unique_web_push_endpoint_hash'\'')
"
')"

IFS=$'\t' read -r web_push_endpoint_hash_column_exists web_push_endpoint_hash_index_exists <<< "${web_push_endpoint_hash_status}"

if [[ "${web_push_subscriptions_exists:-0}" -eq 0 ]]; then
  echo "웹푸시 구독 테이블이 방금 생성되어 endpointHash 마이그레이션을 건너뜁니다."
elif [[ "${web_push_endpoint_hash_column_exists:-0}" -eq 1 && "${web_push_endpoint_hash_index_exists:-0}" -eq 1 ]]; then
  echo "웹푸시 endpointHash 스키마가 이미 반영되어 있어 마이그레이션을 건너뜁니다."
else
  echo "웹푸시 endpointHash 마이그레이션 적용 중..."
  compose_exec exec -T db sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "${WEB_PUSH_ENDPOINT_HASH_MIGRATION_FILE}"
  echo "마이그레이션 적용 완료: $(basename "${WEB_PUSH_ENDPOINT_HASH_MIGRATION_FILE}")"
fi
