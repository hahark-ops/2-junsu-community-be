#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../infra/terraform"

cd "${TF_DIR}"

if [[ -f backend.tf ]]; then
  if [[ -f backend.hcl ]]; then
    terraform init -reconfigure -backend-config=backend.hcl >/dev/null
  elif [[ "${TF_FORCE_LOCAL_BACKEND:-false}" == "true" ]]; then
    terraform init -backend=false >/dev/null
  else
    echo "backend.tf는 있지만 backend.hcl이 없습니다. remote backend를 사용하려면 backend.hcl을 준비하세요."
    echo "정말 로컬 state가 필요하면 TF_FORCE_LOCAL_BACKEND=true 를 명시하세요."
    exit 1
  fi
fi

terraform output
