#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-deploy.proxy.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "env 파일이 없습니다: ${ENV_FILE}"
  exit 1
fi

upsert() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s#^${key}=.*#${key}=${value}#" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

current_value() {
  local key="$1"
  awk -F= -v k="$key" '$1==k {sub($1 FS, ""); print; found=1; exit} END{if(!found) exit 1}' "${ENV_FILE}" 2>/dev/null || true
}

is_placeholder_or_empty() {
  local value="$1"
  [[ -z "${value}" || "${value}" == change_me_* || "${value}" == "http://YOUR_EC2_PUBLIC_IP" ]]
}

ensure_key() {
  local key="$1"
  local default_value="$2"
  local from_env="${!key:-}"
  local current
  current="$(current_value "${key}")"

  if [[ -n "${from_env}" ]]; then
    upsert "${key}" "${from_env}"
    return
  fi

  if is_placeholder_or_empty "${current}"; then
    upsert "${key}" "${default_value}"
  fi
}

ensure_key MYSQL_ROOT_PASSWORD "community_root_password"
ensure_key DB_NAME "community_db"
ensure_key DB_USER "community_user"
ensure_key DB_PASSWORD "community_password"
ensure_key CORS_ALLOW_ORIGINS "http://localhost,http://127.0.0.1"
ensure_key COOKIE_SECURE "false"
ensure_key COOKIE_SAMESITE "lax"
ensure_key COOKIE_MAX_AGE "604800"
ensure_key MAX_UPLOAD_SIZE_BYTES "52428800"
ensure_key MAX_PROFILE_UPLOAD_SIZE_BYTES "31457280"
ensure_key MAX_POST_UPLOAD_SIZE_BYTES "52428800"
ensure_key UPLOAD_PROVIDER "local"
ensure_key UPLOAD_LAMBDA_API_URL ""
ensure_key S3_BUCKET_NAME ""
ensure_key S3_OBJECT_PREFIX "uploads"
ensure_key S3_BASE_URL ""
ensure_key AWS_REGION "ap-northeast-2"
ensure_key AWS_ACCESS_KEY_ID ""
ensure_key AWS_SECRET_ACCESS_KEY ""
ensure_key AWS_SESSION_TOKEN ""
ensure_key BCRYPT_ROUNDS "12"

