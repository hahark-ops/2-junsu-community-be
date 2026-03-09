#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../infra/terraform"
TFVARS_FILE="${1:-terraform.tfvars}"

cd "${TF_DIR}"

terraform_init() {
  local init_args=()

  if [[ -f backend.tf ]]; then
    if [[ -f backend.hcl ]]; then
      echo "remote backend 초기화: backend.hcl"
      init_args=(-reconfigure -backend-config=backend.hcl)
    elif [[ "${TF_FORCE_LOCAL_BACKEND:-false}" == "true" ]]; then
      echo "backend.hcl이 없어 TF_FORCE_LOCAL_BACKEND=true 로 로컬 모드(-backend=false) 초기화합니다."
      init_args=(-backend=false)
    else
      echo "backend.tf는 있지만 backend.hcl이 없습니다. remote backend를 사용하려면 backend.hcl을 준비하세요."
      echo "정말 로컬 state가 필요하면 TF_FORCE_LOCAL_BACKEND=true 를 명시하세요."
      exit 1
    fi
  fi

  terraform init "${init_args[@]}"
}

if [[ ! -f "${TFVARS_FILE}" ]]; then
  echo "tfvars 파일이 없습니다: ${TF_DIR}/${TFVARS_FILE}"
  exit 1
fi

terraform_init
terraform destroy -var-file="${TFVARS_FILE}" -auto-approve

echo
echo "완료: 인프라가 제거되었습니다."
