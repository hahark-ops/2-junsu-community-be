#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_PORT="${NODE_PORT:-30080}"
BASE_URL="${BASE_URL:-http://127.0.0.1:${NODE_PORT}}"
QA_EMAIL="${QA_EMAIL:-qa-local@example.com}"
QA_PASSWORD="${QA_PASSWORD:-Wrong1!A}"
QA_NICKNAME="${QA_NICKNAME:-k8sqa}"

QA_EMAIL="${QA_EMAIL}" \
QA_PASSWORD="${QA_PASSWORD}" \
QA_NICKNAME="${QA_NICKNAME}" \
BASE_URL="${BASE_URL}" \
"${ROOT_DIR}/scripts/qa_ec2_smoke.sh"
