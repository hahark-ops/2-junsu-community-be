#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../infra/terraform"
TFVARS_FILE="${1:-terraform.tfvars}"

cd "${TF_DIR}"

if [[ ! -f "${TFVARS_FILE}" ]]; then
  echo "tfvars 파일이 없습니다: ${TF_DIR}/${TFVARS_FILE}"
  echo "먼저 terraform.tfvars.example 을 복사해서 terraform.tfvars 를 만드세요."
  exit 1
fi

terraform init
terraform validate
terraform plan -var-file="${TFVARS_FILE}" -out=tfplan

echo
echo "완료: plan 결과가 ${TF_DIR}/tfplan 에 저장되었습니다."
