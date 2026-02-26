#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
QA_EMAIL="${QA_EMAIL:-}"
QA_PASSWORD="${QA_PASSWORD:-}"
QA_NICKNAME="${QA_NICKNAME:-awsai}"
RUNTIME_EMAIL="${QA_EMAIL}"
RUNTIME_PASSWORD="${QA_PASSWORD}"

if [[ -z "${QA_EMAIL}" || -z "${QA_PASSWORD}" ]]; then
  echo "Usage: QA_EMAIL=<email> QA_PASSWORD=<password> BASE_URL=<fe_url> $0"
  echo "Example: QA_EMAIL=user@example.com QA_PASSWORD='Abcd1234!' BASE_URL=http://127.0.0.1:3000 $0"
  exit 1
fi

COOKIE_JAR="$(mktemp)"
BODY_FILE="$(mktemp)"
UPLOAD_FILE="$(mktemp "${TMPDIR:-/tmp}/qa-upload.XXXXXX.png")"
trap 'rm -f "${COOKIE_JAR}" "${BODY_FILE}" "${UPLOAD_FILE}"' EXIT

# 1x1 png for upload API smoke test
base64 -d > "${UPLOAD_FILE}" <<'B64'
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2l1xQAAAAASUVORK5CYII=
B64

request_json() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  if [[ -n "${data}" ]]; then
    curl -sS -o "${BODY_FILE}" -w "%{http_code}" \
      -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" \
      -X "${method}" "${BASE_URL}${path}" \
      -H "Content-Type: application/json" \
      --data "${data}"
  else
    curl -sS -o "${BODY_FILE}" -w "%{http_code}" \
      -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" \
      -X "${method}" "${BASE_URL}${path}"
  fi
}

normalize_nickname() {
  local raw="$1"
  local normalized
  normalized="$(printf "%s" "${raw}" | tr -cd '[:alnum:]' | cut -c1-10)"
  if [[ -z "${normalized}" ]]; then
    normalized="qa$(date +%H%M%S)"
    normalized="$(printf "%s" "${normalized}" | cut -c1-10)"
  fi
  printf "%s" "${normalized}"
}

request_multipart_upload() {
  local path="$1"
  curl -sS -o "${BODY_FILE}" -w "%{http_code}" \
    -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" \
    -X POST "${BASE_URL}${path}" \
    -F "file=@${UPLOAD_FILE};type=image/png" \
    -F "type=profile"
}

expect_status() {
  local actual="$1"
  local expected_regex="$2"
  local label="$3"
  if [[ ! "${actual}" =~ ^(${expected_regex})$ ]]; then
    echo "[FAIL] ${label}: expected ${expected_regex}, got ${actual}"
    echo "----- response body -----"
    cat "${BODY_FILE}"
    echo
    exit 1
  fi
  echo "[PASS] ${label} (status ${actual})"
}

wait_for_status() {
  local method="$1"
  local path="$2"
  local expected_regex="$3"
  local label="$4"
  local max_retries="${5:-20}"
  local sleep_seconds="${6:-2}"
  local attempt=1
  local status=""

  while [[ "${attempt}" -le "${max_retries}" ]]; do
    status="$(request_json "${method}" "${path}")"
    if [[ "${status}" =~ ^(${expected_regex})$ ]]; then
      echo "[PASS] ${label} ready (status ${status}, attempt ${attempt}/${max_retries})"
      return 0
    fi
    echo "[INFO] ${label} not ready yet (status ${status}, attempt ${attempt}/${max_retries})"
    attempt=$((attempt + 1))
    sleep "${sleep_seconds}"
  done

  echo "[FAIL] ${label} readiness timeout: expected ${expected_regex}, got ${status}"
  echo "----- response body -----"
  cat "${BODY_FILE}"
  echo
  exit 1
}

json_field() {
  local field="$1"
  python3 - "${field}" "${BODY_FILE}" <<'PY'
import json
import sys

field = sys.argv[1]
path = sys.argv[2]

with open(path, "r", encoding="utf-8") as f:
    obj = json.load(f)

cur = obj
for part in field.split("."):
    if part == "":
        continue
    if isinstance(cur, dict):
        cur = cur.get(part)
    elif isinstance(cur, list):
        try:
            idx = int(part)
        except ValueError:
            cur = None
            break
        if idx < 0 or idx >= len(cur):
            cur = None
            break
        cur = cur[idx]
    else:
        cur = None
        break

if cur is None:
    sys.exit(1)

if isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
else:
    print(cur)
PY
}

json_field_or_empty() {
  local field="$1"
  python3 - "${field}" "${BODY_FILE}" <<'PY'
import json
import sys

field = sys.argv[1]
path = sys.argv[2]

try:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
except Exception:
    print("")
    sys.exit(0)

cur = obj
for part in field.split("."):
    if part == "":
        continue
    if isinstance(cur, dict):
        cur = cur.get(part)
    elif isinstance(cur, list):
        try:
            idx = int(part)
        except ValueError:
            cur = None
            break
        if idx < 0 or idx >= len(cur):
            cur = None
            break
        cur = cur[idx]
    else:
        cur = None
        break

if cur is None:
    print("")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
else:
    print(cur)
PY
}

echo "== QA start =="
echo "BASE_URL=${BASE_URL}"

status="$(request_json GET "/")"
expect_status "${status}" "200" "health check"

wait_for_status GET "/v1/posts" "200" "public posts api" 20 2

status="$(request_json GET "/v1/posts")"
expect_status "${status}" "200" "public posts list"

status="$(request_json GET "/v1/auth/me")"
expect_status "${status}" "401" "me before login should fail"

login_payload="$(cat <<JSON
{"email":"${RUNTIME_EMAIL}","password":"${RUNTIME_PASSWORD}"}
JSON
)"
status="$(request_json POST "/v1/auth/login" "${login_payload}")"
if [[ "${status}" != "200" ]]; then
  error_code="$(json_field_or_empty "code")"
  if [[ "${status}" == "400" && "${error_code}" == "LOGIN_FAILED" ]]; then
    echo "[INFO] 기본 QA 계정 로그인 실패. fallback QA 계정 생성 후 재시도합니다."
    ts_fallback="$(date +%s)"
    RUNTIME_EMAIL="qa${ts_fallback}@example.com"
    RUNTIME_PASSWORD="Qa!${ts_fallback}Aa1"
    QA_NICKNAME="$(normalize_nickname "${QA_NICKNAME}")"
    fallback_nickname="$(normalize_nickname "${QA_NICKNAME}${ts_fallback}")"

    signup_payload="$(cat <<JSON
{"email":"${RUNTIME_EMAIL}","password":"${RUNTIME_PASSWORD}","nickname":"${fallback_nickname}"}
JSON
)"
    status="$(request_json POST "/v1/auth/signup" "${signup_payload}")"
    expect_status "${status}" "201" "fallback signup"

    login_payload="$(cat <<JSON
{"email":"${RUNTIME_EMAIL}","password":"${RUNTIME_PASSWORD}"}
JSON
)"
    status="$(request_json POST "/v1/auth/login" "${login_payload}")"
    expect_status "${status}" "200" "login (fallback user)"
    QA_NICKNAME="${fallback_nickname}"
  else
    expect_status "${status}" "200" "login"
  fi
else
  echo "[PASS] login (status ${status})"
fi

status="$(request_json GET "/v1/auth/me")"
expect_status "${status}" "200" "me after login"
USER_ID="$(json_field "data.userId")"
echo "[INFO] userId=${USER_ID}"

ts="$(date +%s)"
create_post_payload="$(cat <<JSON
{"title":"QA smoke ${ts}","content":"QA smoke content ${ts}"}
JSON
)"
status="$(request_json POST "/v1/posts" "${create_post_payload}")"
expect_status "${status}" "201" "create post"
POST_ID="$(json_field "data.postId")"
echo "[INFO] postId=${POST_ID}"

status="$(request_json GET "/v1/posts/${POST_ID}?increase_view=false")"
expect_status "${status}" "200" "post detail (no view increase) #1"
VIEW1="$(json_field "data.viewCount")"

status="$(request_json GET "/v1/posts/${POST_ID}?increase_view=false")"
expect_status "${status}" "200" "post detail (no view increase) #2"
VIEW2="$(json_field "data.viewCount")"
if [[ "${VIEW1}" != "${VIEW2}" ]]; then
  echo "[FAIL] increase_view=false should not increase view count (${VIEW1} -> ${VIEW2})"
  exit 1
fi
echo "[PASS] increase_view=false keeps view count (${VIEW1})"

create_comment_payload='{"content":"QA smoke comment"}'
status="$(request_json POST "/v1/posts/${POST_ID}/comments" "${create_comment_payload}")"
expect_status "${status}" "201" "create comment"
COMMENT_ID="$(json_field "data.commentId")"
echo "[INFO] commentId=${COMMENT_ID}"

status="$(request_json PATCH "/v1/posts/${POST_ID}/comments/${COMMENT_ID}" '{"content":"QA smoke comment updated"}')"
expect_status "${status}" "200" "update comment"

status="$(request_json POST "/v1/posts/${POST_ID}/likes")"
expect_status "${status}" "201" "like post"

status="$(request_json DELETE "/v1/posts/${POST_ID}/likes")"
expect_status "${status}" "200" "unlike post"

status="$(request_multipart_upload "/v1/files/upload")"
expect_status "${status}" "200" "upload profile image"
FILE_URL="$(json_field "fileUrl")"
echo "[INFO] uploaded fileUrl=${FILE_URL}"

update_user_payload="$(cat <<JSON
{"nickname":"$(normalize_nickname "${QA_NICKNAME}")","profileImage":"${FILE_URL}"}
JSON
)"
status="$(request_json PATCH "/v1/users/${USER_ID}" "${update_user_payload}")"
expect_status "${status}" "200" "update profile with uploaded image"

status="$(request_json DELETE "/v1/posts/${POST_ID}/comments/${COMMENT_ID}")"
expect_status "${status}" "200" "delete comment"

status="$(request_json DELETE "/v1/posts/${POST_ID}")"
expect_status "${status}" "200" "delete post"

status="$(request_json POST "/v1/auth/logout")"
expect_status "${status}" "200" "logout"

status="$(request_json GET "/v1/auth/me")"
expect_status "${status}" "401" "me after logout should fail"

echo "== QA done: PASS =="
