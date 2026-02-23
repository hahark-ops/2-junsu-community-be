#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <upload_api_route_url> <file_path> [profile|post]"
  echo "Example: $0 https://xxxx.execute-api.ap-northeast-2.amazonaws.com/v1/files/upload ./sample.png profile"
  exit 1
fi

UPLOAD_API_URL="$1"
FILE_PATH="$2"
UPLOAD_TYPE="${3:-profile}"

if [[ ! -f "${FILE_PATH}" ]]; then
  echo "파일이 없습니다: ${FILE_PATH}"
  exit 1
fi

RESP_FILE="$(mktemp)"
trap 'rm -f "${RESP_FILE}"' EXIT

HTTP_CODE="$(curl -sS -o "${RESP_FILE}" -w "%{http_code}" \
  -F "file=@${FILE_PATH}" \
  -F "type=${UPLOAD_TYPE}" \
  -X POST "${UPLOAD_API_URL}" \
  )"

if [[ "${HTTP_CODE}" != "200" && "${HTTP_CODE}" != "201" ]]; then
  echo "Lambda 업로드 실패 (status=${HTTP_CODE})"
  cat "${RESP_FILE}"
  echo
  exit 1
fi

FILE_URL="$(python3 - <<'PY' "${RESP_FILE}"
import json, sys
data=json.load(open(sys.argv[1]))
print(
  data.get("data", {}).get("fileUrl")
  or data.get("data", {}).get("filePath")
  or data.get("fileUrl")
  or data.get("filePath")
)
PY
)"

echo "업로드 성공"
echo "fileUrl=${FILE_URL}"
