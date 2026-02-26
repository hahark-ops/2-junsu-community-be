#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/deploy.env}"
ECR_LOGIN="${ECR_LOGIN:-false}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "배포 env 파일이 없습니다: ${ENV_FILE}"
  echo "예시 생성: cp ${ROOT_DIR}/deploy.env.example ${ROOT_DIR}/deploy.env"
  exit 1
fi

required_keys=(
  BE_IMAGE
  FE_IMAGE
  DB_IMAGE
  MYSQL_ROOT_PASSWORD
  DB_NAME
  DB_USER
  DB_PASSWORD
  CORS_ALLOW_ORIGINS
)

for key in "${required_keys[@]}"; do
  if ! grep -Eq "^${key}=.+" "${ENV_FILE}"; then
    echo "env 파일 필수 키가 누락되었거나 비어 있습니다: ${key}"
    exit 1
  fi
done

if [[ "${ECR_LOGIN}" == "true" ]]; then
  be_image="$(grep -E '^BE_IMAGE=' "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"
  registry="${be_image%%/*}"

  if [[ "${registry}" == *.amazonaws.com ]]; then
    aws_region="${AWS_REGION:-$(echo "${registry}" | awk -F. '{print $(NF-2)}')}"
    echo "ECR 로그인 수행: ${registry} (region=${aws_region})"
    aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${registry}"
  fi
fi

cd "${ROOT_DIR}"
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml pull
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml up -d
./scripts/run_migrations.sh "${ROOT_DIR}/docker-compose.deploy.yml" "${ENV_FILE}"
docker compose --env-file "${ENV_FILE}" -f docker-compose.deploy.yml ps
