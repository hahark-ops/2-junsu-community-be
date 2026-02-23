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
terraform apply -var-file="${TFVARS_FILE}" -auto-approve

echo
echo "완료: 인프라가 생성/업데이트되었습니다."
echo "다음: ./scripts/infra_outputs.sh 로 접속 정보 확인"
