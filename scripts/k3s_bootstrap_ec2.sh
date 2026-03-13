#!/usr/bin/env bash
set -euo pipefail

INSTANCE_ID="${1:-}"
REMOTE_DIR="${REMOTE_DIR:-/opt/2-junsu-community-be}"

if [[ -z "${INSTANCE_ID}" ]]; then
  echo "사용법: $0 <instance-id>"
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

SSM_PARAMETERS="$(build_ssm_parameters \
  "set -euo pipefail" \
  "if command -v docker >/dev/null 2>&1 && [ -f \"${REMOTE_DIR}/docker-compose.reverse-proxy.yml\" ]; then" \
  "  cd \"${REMOTE_DIR}\" || exit 1" \
  "  if [ -f deploy.proxy.env ]; then" \
  "    docker compose --env-file deploy.proxy.env -f docker-compose.reverse-proxy.yml down || true" \
  "  fi" \
  "fi" \
  "if ! command -v curl >/dev/null 2>&1; then" \
  "  sudo dnf install -y curl >/dev/null 2>&1 || sudo yum install -y curl >/dev/null 2>&1" \
  "fi" \
  "sudo mkdir -p /etc/rancher/k3s" \
  "cat <<'EOF' | sudo tee /etc/rancher/k3s/config.yaml >/dev/null" \
  "write-kubeconfig-mode: \"644\"" \
  "tls-san:" \
  "  - \"${PUBLIC_IP}\"" \
  "EOF" \
  "if ! systemctl is-active --quiet k3s; then" \
  "  curl -sfL https://get.k3s.io | sh -" \
  "fi" \
  "sudo systemctl enable k3s >/dev/null 2>&1 || true" \
  "sudo systemctl restart k3s" \
  "for _ in \$(seq 1 90); do" \
  "  if sudo /usr/local/bin/k3s kubectl get nodes >/dev/null 2>&1; then" \
  "    break" \
  "  fi" \
  "  sleep 2" \
  "done" \
  "sudo /usr/local/bin/k3s kubectl wait --for=condition=Ready node --all --timeout=180s" \
)"

COMMAND_ID="$(
  aws ssm send-command \
    --instance-ids "${INSTANCE_ID}" \
    --document-name "AWS-RunShellScript" \
    --comment "Install k3s and stop docker compose app stack" \
    --parameters "${SSM_PARAMETERS}" \
    --query 'Command.CommandId' \
    --output text
)"

wait_ssm_command "${COMMAND_ID}" "${INSTANCE_ID}"

echo "[PASS] k3s bootstrap 완료: ${INSTANCE_ID}"
