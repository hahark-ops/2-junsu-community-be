#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$(cd "${ROOT_DIR}/.." && pwd)"

REGISTRY="${REGISTRY:-}"
TAG="${TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"

if [[ -z "${REGISTRY}" ]]; then
  echo "REGISTRY 환경변수가 필요합니다. 예: REGISTRY=docker.io/<dockerhub_id>"
  exit 1
fi

BE_IMAGE="${REGISTRY}/community-be:${TAG}"
FE_IMAGE="${REGISTRY}/community-fe:${TAG}"
DB_IMAGE="${REGISTRY}/community-db:${TAG}"

echo "Push target:"
echo "  ${BE_IMAGE}"
echo "  ${FE_IMAGE}"
echo "  ${DB_IMAGE}"

if [[ "${REGISTRY}" == *.amazonaws.com ]]; then
  AWS_REGION="${AWS_REGION:-$(echo "${REGISTRY}" | awk -F. '{print $(NF-2)}')}"
  echo "ECR 로그인: ${REGISTRY} (region=${AWS_REGION})"
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${REGISTRY}"
fi

if docker buildx version >/dev/null 2>&1; then
  docker buildx build --platform "${PLATFORM}" -t "${BE_IMAGE}" --push -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"
  docker buildx build --platform "${PLATFORM}" -t "${FE_IMAGE}" --push -f "${ROOT_DIR}/docker/fe.Dockerfile" "${DESKTOP_DIR}"
  docker buildx build --platform "${PLATFORM}" -t "${DB_IMAGE}" --push -f "${ROOT_DIR}/docker/db.Dockerfile" "${ROOT_DIR}"
else
  docker build -t "${BE_IMAGE}" -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"
  docker build -t "${FE_IMAGE}" -f "${ROOT_DIR}/docker/fe.Dockerfile" "${DESKTOP_DIR}"
  docker build -t "${DB_IMAGE}" -f "${ROOT_DIR}/docker/db.Dockerfile" "${ROOT_DIR}"
  docker push "${BE_IMAGE}"
  docker push "${FE_IMAGE}"
  docker push "${DB_IMAGE}"
fi

echo "이미지 푸시 완료"
