#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../infra/terraform"

cd "${TF_DIR}"

if [[ -f backend.tf ]]; then
  if [[ -f backend.hcl ]]; then
    terraform init -reconfigure -backend-config=backend.hcl >/dev/null
  else
    terraform init -backend=false >/dev/null
  fi
fi

terraform output
