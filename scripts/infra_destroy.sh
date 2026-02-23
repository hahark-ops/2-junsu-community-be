#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../infra/terraform"
TFVARS_FILE="${1:-terraform.tfvars}"

cd "${TF_DIR}"

if [[ ! -f "${TFVARS_FILE}" ]]; then
  echo "tfvars 파일이 없습니다: ${TF_DIR}/${TFVARS_FILE}"
  exit 1
fi

terraform init
terraform destroy -var-file="${TFVARS_FILE}" -auto-approve

echo
echo "완료: 인프라가 제거되었습니다."
