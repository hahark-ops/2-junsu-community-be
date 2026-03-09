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
SOURCE_SHA="${SOURCE_SHA:-}"
FE_REF="${FE_REF:-}"

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

if [[ -z "${SOURCE_SHA}" ]]; then
  SSM_PARAM_LAST_SHA="${SSM_PARAM_LAST_SHA:-}"
  if [[ -z "${SSM_PARAM_LAST_SHA}" ]]; then
    if [[ "${DEPLOY_ENV}" == "prod" ]]; then
      SSM_PARAM_LAST_SHA="/community/prod/deploy/last_success_sha"
    else
      SSM_PARAM_LAST_SHA="/community/dev/deploy/last_success_sha"
    fi
  fi

  SOURCE_SHA="$(aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "${SSM_PARAM_LAST_SHA}" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || true)"
fi

if [[ -z "${FE_REF}" ]]; then
  SSM_PARAM_LAST_FE_SHA="${SSM_PARAM_LAST_FE_SHA:-}"
  if [[ -z "${SSM_PARAM_LAST_FE_SHA}" ]]; then
    if [[ "${DEPLOY_ENV}" == "prod" ]]; then
      SSM_PARAM_LAST_FE_SHA="/community/prod/deploy/last_success_fe_sha"
    else
      SSM_PARAM_LAST_FE_SHA="/community/dev/deploy/last_success_fe_sha"
    fi
  fi

  FE_REF="$(aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "${SSM_PARAM_LAST_FE_SHA}" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || true)"
fi

if [[ -z "${IMAGE_TAG}" || "${IMAGE_TAG}" == "None" ]]; then
  echo "동일 태그를 찾지 못했습니다."
  echo "IMAGE_TAG를 직접 지정하거나 SSM 파라미터를 확인하세요."
  exit 1
fi

if [[ -z "${SOURCE_SHA}" || "${SOURCE_SHA}" == "None" ]]; then
  echo "동일 태그의 source SHA를 찾지 못했습니다."
  exit 1
fi

if [[ -z "${FE_REF}" || "${FE_REF}" == "None" ]]; then
  echo "동일 태그의 FE SHA를 찾지 못했습니다."
  exit 1
fi

echo "[INFO] Trigger deploy workflow"
echo "  workflow: ${WORKFLOW_FILE}"
echo "  ref: ${WORKFLOW_REF}"
echo "  environment: ${DEPLOY_ENV}"
echo "  image_tag: ${IMAGE_TAG}"
echo "  source_sha: ${SOURCE_SHA}"
echo "  fe_ref: ${FE_REF}"

gh workflow run "${WORKFLOW_FILE}" \
  --ref "${WORKFLOW_REF}" \
  -f environment="${DEPLOY_ENV}" \
  -f image_tag="${IMAGE_TAG}" \
  -f source_sha="${SOURCE_SHA}" \
  -f fe_ref="${FE_REF}" \
  -f reuse_existing_images=true \
  -f rollback_on_fail="${ROLLBACK_ON_FAIL}"

echo
echo "[INFO] 최근 deploy-ec2 실행 내역"
gh run list --workflow "${WORKFLOW_FILE}" --limit 5
