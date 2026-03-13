#!/usr/bin/env bash
set -euo pipefail

INSTANCE_ID="${1:-}"
REMOTE_ENV_PATH="${2:-/opt/2-junsu-community-be/deploy.proxy.env}"
OUTPUT_PATH="${3:-}"

if [[ -z "${INSTANCE_ID}" ]]; then
  echo "사용법: $0 <instance-id> [remote-env-path] [output-path]"
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 명령이 필요합니다."
    exit 1
  fi
}

build_ssm_parameters() {
  python3 - "$@" <<'PY'
import json
import sys

print(json.dumps({"commands": sys.argv[1:]}))
PY
}

wait_ssm_command() {
  local command_id="$1"
  local instance_id="$2"

  for _ in $(seq 1 120); do
    local status
    status="$(aws ssm get-command-invocation --command-id "${command_id}" --instance-id "${instance_id}" --query 'Status' --output text 2>/dev/null || true)"
    case "${status}" in
      Success)
        return 0
        ;;
      Failed|Cancelled|TimedOut|Undeliverable|Terminated)
        aws ssm get-command-invocation --command-id "${command_id}" --instance-id "${instance_id}" --query 'StandardErrorContent' --output text || true
        return 1
        ;;
    esac
    sleep 2
  done

  echo "SSM 명령 대기 시간이 초과되었습니다."
  return 1
}

require_cmd aws
require_cmd python3

if [[ -z "${OUTPUT_PATH}" ]]; then
  OUTPUT_PATH="/tmp/k3s-${INSTANCE_ID}.env"
fi

COMMAND_ID="$(
  aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name "AWS-RunShellScript" \
    --comment "Read deploy env for k3s" \
    --parameters "$(build_ssm_parameters "sudo cat ${REMOTE_ENV_PATH}")" \
    --query 'Command.CommandId' \
    --output text
)"

wait_ssm_command "${COMMAND_ID}" "${INSTANCE_ID}"

aws ssm get-command-invocation \
  --command-id "${COMMAND_ID}" \
  --instance-id "${INSTANCE_ID}" \
  --query 'StandardOutputContent' \
  --output text > "${OUTPUT_PATH}"

echo "${OUTPUT_PATH}"
