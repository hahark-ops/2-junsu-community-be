#!/usr/bin/env bash
set -euo pipefail

# Trigger deploy-ec2 workflow with the same image tag.
# Priority:
# 1) IMAGE_TAG env
# 2) SSM parameter value
#
# Usage:
#   IMAGE_TAG=securefix-20260303-1 ./scripts/redeploy_same_tag_ec2.sh
#   DEPLOY_ENV=dev ./scripts/redeploy_same_tag_ec2.sh

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI가 필요합니다. (brew install gh)"
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI가 필요합니다."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh 인증이 필요합니다. (gh auth login)"
  exit 1
fi

DEPLOY_ENV="${DEPLOY_ENV:-dev}"
WORKFLOW_FILE="${WORKFLOW_FILE:-deploy-ec2.yml}"
WORKFLOW_REF="${WORKFLOW_REF:-main}"
ROLLBACK_ON_FAIL="${ROLLBACK_ON_FAIL:-true}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
IMAGE_TAG="${IMAGE_TAG:-}"

if [[ -z "${IMAGE_TAG}" ]]; then
  SSM_PARAM_LAST_TAG="${SSM_PARAM_LAST_TAG:-}"
  if [[ -z "${SSM_PARAM_LAST_TAG}" ]]; then
    if [[ "${DEPLOY_ENV}" == "prod" ]]; then
      SSM_PARAM_LAST_TAG="/community/prod/deploy/last_success_tag"
    else
      SSM_PARAM_LAST_TAG="/community/dev/deploy/last_success_tag"
    fi
  fi

  IMAGE_TAG="$(aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "${SSM_PARAM_LAST_TAG}" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || true)"
fi

if [[ -z "${IMAGE_TAG}" || "${IMAGE_TAG}" == "None" ]]; then
  echo "동일 태그를 찾지 못했습니다."
  echo "IMAGE_TAG를 직접 지정하거나 SSM 파라미터를 확인하세요."
  exit 1
fi

echo "[INFO] Trigger deploy workflow"
echo "  workflow: ${WORKFLOW_FILE}"
echo "  ref: ${WORKFLOW_REF}"
echo "  environment: ${DEPLOY_ENV}"
echo "  image_tag: ${IMAGE_TAG}"

gh workflow run "${WORKFLOW_FILE}" \
  --ref "${WORKFLOW_REF}" \
  -f environment="${DEPLOY_ENV}" \
  -f image_tag="${IMAGE_TAG}" \
  -f rollback_on_fail="${ROLLBACK_ON_FAIL}"

echo
echo "[INFO] 최근 deploy-ec2 실행 내역"
gh run list --workflow "${WORKFLOW_FILE}" --limit 5
