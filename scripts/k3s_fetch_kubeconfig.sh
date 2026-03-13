#!/usr/bin/env bash
set -euo pipefail

INSTANCE_ID="${1:-}"
OUTPUT_PATH="${2:-}"

if [[ -z "${INSTANCE_ID}" ]]; then
  echo "사용법: $0 <instance-id> [output-path]"
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
  OUTPUT_PATH="/tmp/k3s-${INSTANCE_ID}.yaml"
fi

PUBLIC_IP="$(
  aws ec2 describe-instances \
    --instance-ids "${INSTANCE_ID}" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text
)"

if [[ -z "${PUBLIC_IP}" || "${PUBLIC_IP}" == "None" ]]; then
  echo "인스턴스의 Public IP를 찾을 수 없습니다: ${INSTANCE_ID}"
  exit 1
fi

COMMAND_ID="$(
  aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name "AWS-RunShellScript" \
    --comment "Read k3s kubeconfig" \
    --parameters "$(build_ssm_parameters "sudo cat /etc/rancher/k3s/k3s.yaml | base64 -w0")" \
    --query 'Command.CommandId' \
    --output text
)"

wait_ssm_command "${COMMAND_ID}" "${INSTANCE_ID}"

ENCODED_CONTENT="$(
  aws ssm get-command-invocation \
    --command-id "${COMMAND_ID}" \
    --instance-id "${INSTANCE_ID}" \
    --query 'StandardOutputContent' \
    --output text
)"

python3 - "${OUTPUT_PATH}" "${PUBLIC_IP}" "${ENCODED_CONTENT}" <<'PY'
from pathlib import Path
import base64
import sys

path = Path(sys.argv[1])
public_ip = sys.argv[2]
encoded = sys.argv[3]

content = base64.b64decode(encoded.encode()).decode()
content = content.replace("127.0.0.1", public_ip)
path.write_text(content)
PY

python3 - "${OUTPUT_PATH}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
content = path.read_text()
if "current-context:" not in content or "server: https://" not in content:
    raise SystemExit("kubeconfig export failed")
PY

echo "${OUTPUT_PATH}"
