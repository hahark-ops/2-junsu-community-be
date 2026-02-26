#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_FE_DIR="${ROOT_DIR}/../2-junsu-community-fe"
FE_DIR="${FE_DIR:-${DEFAULT_FE_DIR}}"

REGISTRY="${REGISTRY:-}"
TAG="${TAG:-}"
PLATFORM="${PLATFORM:-linux/amd64}"

if [[ -z "${REGISTRY}" ]]; then
  echo "REGISTRY 환경변수가 필요합니다. 예: REGISTRY=docker.io/<dockerhub_id>"
  exit 1
fi

if [[ -z "${TAG}" ]]; then
  if git -C "${ROOT_DIR}" rev-parse --short HEAD >/dev/null 2>&1; then
    TAG="sha-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)"
  else
    TAG="sha-$(date +%s)"
  fi
fi

BE_IMAGE="${REGISTRY}/community-be:${TAG}"
FE_IMAGE="${REGISTRY}/community-fe:${TAG}"
DB_IMAGE="${REGISTRY}/community-db:${TAG}"

if [[ ! -d "${FE_DIR}" ]]; then
  echo "FE_DIR 경로를 찾지 못했습니다: ${FE_DIR}"
  echo "예: FE_DIR=/path/to/2-junsu-community-fe REGISTRY=docker.io/<id> TAG=v1 ./scripts/push_images.sh"
  exit 1
fi

if [[ ! -f "${FE_DIR}/Dockerfile" ]]; then
  echo "FE Dockerfile을 찾지 못했습니다: ${FE_DIR}/Dockerfile"
  exit 1
fi

echo "Push target:"
echo "  ${BE_IMAGE}"
echo "  ${FE_IMAGE}"
echo "  ${DB_IMAGE}"
echo "FE build dir: ${FE_DIR}"

if [[ "${REGISTRY}" == *.amazonaws.com ]]; then
  AWS_REGION="${AWS_REGION:-$(echo "${REGISTRY}" | awk -F. '{print $(NF-2)}')}"
  echo "ECR 로그인: ${REGISTRY} (region=${AWS_REGION})"
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${REGISTRY}"
fi

if docker buildx version >/dev/null 2>&1; then
  docker buildx build --platform "${PLATFORM}" -t "${BE_IMAGE}" --push -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"
  docker buildx build --platform "${PLATFORM}" -t "${FE_IMAGE}" --push -f "${FE_DIR}/Dockerfile" "${FE_DIR}"
  docker buildx build --platform "${PLATFORM}" -t "${DB_IMAGE}" --push -f "${ROOT_DIR}/docker/db.Dockerfile" "${ROOT_DIR}"
else
  docker build -t "${BE_IMAGE}" -f "${ROOT_DIR}/Dockerfile" "${ROOT_DIR}"
  docker build -t "${FE_IMAGE}" -f "${FE_DIR}/Dockerfile" "${FE_DIR}"
  docker build -t "${DB_IMAGE}" -f "${ROOT_DIR}/docker/db.Dockerfile" "${ROOT_DIR}"
  docker push "${BE_IMAGE}"
  docker push "${FE_IMAGE}"
  docker push "${DB_IMAGE}"
fi

echo "이미지 푸시 완료"
