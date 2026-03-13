#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="${ROOT_DIR}/k8s"
DEFAULT_FE_DIR="${ROOT_DIR}/../2-junsu-community-fe"

INSTANCE_ID="${INSTANCE_ID:-}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-}"
OVERLAY="${OVERLAY:-k3s-rolling}"
NAMESPACE="${NAMESPACE:-community-k3s}"
REGISTRY="${REGISTRY:-}"
TAG="${TAG:-}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
FE_DIR="${FE_DIR:-${DEFAULT_FE_DIR}}"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-}"
REMOTE_ENV_PATH="${REMOTE_ENV_PATH:-/opt/2-junsu-community-be/deploy.proxy.env}"
CORS_ALLOW_ORIGINS_OVERRIDE="${CORS_ALLOW_ORIGINS_OVERRIDE:-}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 명령이 필요합니다."
    exit 1
  fi
}

env_get() {
  local file="$1"
  local key="$2"
  awk -F= -v k="$key" '$1==k {sub($1 FS, ""); print; exit}' "${file}"
}

need_value() {
  local value="$1"
  local label="$2"
  if [[ -z "${value}" ]]; then
    echo "${label} 값이 필요합니다."
    exit 1
  fi
}

require_cmd aws
require_cmd kubectl
require_cmd docker
require_cmd mktemp

delete_if_exists() {
  local namespace="$1"
  shift
  for resource in "$@"; do
    kubectl -n "${namespace}" delete "${resource}" --ignore-not-found --wait=true >/dev/null 2>&1 || true
  done
}

case "${OVERLAY}" in
  k3s-rolling|k3s-bluegreen)
    ;;
  *)
    echo "지원하지 않는 OVERLAY입니다: ${OVERLAY}"
    echo "허용: k3s-rolling, k3s-bluegreen"
    exit 1
    ;;
esac

need_value "${REGISTRY}" "REGISTRY"

if [[ -z "${TAG}" ]]; then
  TAG="sha-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)"
fi

if [[ -z "${KUBECONFIG_PATH}" ]]; then
  need_value "${INSTANCE_ID}" "INSTANCE_ID 또는 KUBECONFIG_PATH"
  KUBECONFIG_PATH="$("${ROOT_DIR}/scripts/k3s_fetch_kubeconfig.sh" "${INSTANCE_ID}")"
fi

if [[ -z "${DEPLOY_ENV_FILE}" ]]; then
  need_value "${INSTANCE_ID}" "INSTANCE_ID 또는 DEPLOY_ENV_FILE"
  DEPLOY_ENV_FILE="$("${ROOT_DIR}/scripts/k3s_export_remote_env.sh" "${INSTANCE_ID}" "${REMOTE_ENV_PATH}")"
fi

if [[ ! -f "${DEPLOY_ENV_FILE}" ]]; then
  echo "DEPLOY_ENV_FILE을 찾을 수 없습니다: ${DEPLOY_ENV_FILE}"
  exit 1
fi

BE_IMAGE="${REGISTRY}/community-be:${TAG}"
FE_IMAGE="${REGISTRY}/community-fe:${TAG}"
DB_IMAGE="${REGISTRY}/community-db:${TAG}"

REGISTRY="${REGISTRY}" TAG="${TAG}" AWS_REGION="${AWS_REGION}" FE_DIR="${FE_DIR}" "${ROOT_DIR}/scripts/push_images.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
cp -R "${K8S_DIR}" "${TMP_DIR}/k8s"

DB_NAME="$(env_get "${DEPLOY_ENV_FILE}" DB_NAME)"
DB_USER="$(env_get "${DEPLOY_ENV_FILE}" DB_USER)"
MYSQL_ROOT_PASSWORD="$(env_get "${DEPLOY_ENV_FILE}" MYSQL_ROOT_PASSWORD)"
DB_PASSWORD="$(env_get "${DEPLOY_ENV_FILE}" DB_PASSWORD)"
COOKIE_SECURE="$(env_get "${DEPLOY_ENV_FILE}" COOKIE_SECURE)"
COOKIE_SAMESITE="$(env_get "${DEPLOY_ENV_FILE}" COOKIE_SAMESITE)"
COOKIE_MAX_AGE="$(env_get "${DEPLOY_ENV_FILE}" COOKIE_MAX_AGE)"
MAX_UPLOAD_SIZE_BYTES="$(env_get "${DEPLOY_ENV_FILE}" MAX_UPLOAD_SIZE_BYTES)"
MAX_PROFILE_UPLOAD_SIZE_BYTES="$(env_get "${DEPLOY_ENV_FILE}" MAX_PROFILE_UPLOAD_SIZE_BYTES)"
MAX_POST_UPLOAD_SIZE_BYTES="$(env_get "${DEPLOY_ENV_FILE}" MAX_POST_UPLOAD_SIZE_BYTES)"
UPLOAD_PROVIDER="$(env_get "${DEPLOY_ENV_FILE}" UPLOAD_PROVIDER)"
UPLOAD_LAMBDA_API_URL="$(env_get "${DEPLOY_ENV_FILE}" UPLOAD_LAMBDA_API_URL)"
UPLOAD_INTERNAL_TOKEN="$(env_get "${DEPLOY_ENV_FILE}" UPLOAD_INTERNAL_TOKEN)"
S3_BUCKET_NAME="$(env_get "${DEPLOY_ENV_FILE}" S3_BUCKET_NAME)"
S3_OBJECT_PREFIX="$(env_get "${DEPLOY_ENV_FILE}" S3_OBJECT_PREFIX)"
S3_BASE_URL="$(env_get "${DEPLOY_ENV_FILE}" S3_BASE_URL)"
AWS_ACCESS_KEY_ID_VALUE="$(env_get "${DEPLOY_ENV_FILE}" AWS_ACCESS_KEY_ID)"
AWS_SECRET_ACCESS_KEY_VALUE="$(env_get "${DEPLOY_ENV_FILE}" AWS_SECRET_ACCESS_KEY)"
AWS_SESSION_TOKEN_VALUE="$(env_get "${DEPLOY_ENV_FILE}" AWS_SESSION_TOKEN)"
BCRYPT_ROUNDS="$(env_get "${DEPLOY_ENV_FILE}" BCRYPT_ROUNDS)"
WEB_PUSH_VAPID_PUBLIC_KEY="$(env_get "${DEPLOY_ENV_FILE}" WEB_PUSH_VAPID_PUBLIC_KEY)"
WEB_PUSH_VAPID_PRIVATE_KEY="$(env_get "${DEPLOY_ENV_FILE}" WEB_PUSH_VAPID_PRIVATE_KEY)"
WEB_PUSH_SUBJECT="$(env_get "${DEPLOY_ENV_FILE}" WEB_PUSH_SUBJECT)"

if [[ -n "${CORS_ALLOW_ORIGINS_OVERRIDE}" ]]; then
  CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS_OVERRIDE}"
else
  CORS_ALLOW_ORIGINS="$(env_get "${DEPLOY_ENV_FILE}" CORS_ALLOW_ORIGINS)"
fi

cat > "${TMP_DIR}/k8s/base/config/app.env" <<EOF
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
REDIS_URL=redis://community-redis:6379/0
CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS}
COOKIE_SECURE=${COOKIE_SECURE}
COOKIE_SAMESITE=${COOKIE_SAMESITE}
COOKIE_MAX_AGE=${COOKIE_MAX_AGE}
MAX_UPLOAD_SIZE_BYTES=${MAX_UPLOAD_SIZE_BYTES}
MAX_PROFILE_UPLOAD_SIZE_BYTES=${MAX_PROFILE_UPLOAD_SIZE_BYTES}
MAX_POST_UPLOAD_SIZE_BYTES=${MAX_POST_UPLOAD_SIZE_BYTES}
UPLOAD_PROVIDER=${UPLOAD_PROVIDER}
UPLOAD_LAMBDA_API_URL=${UPLOAD_LAMBDA_API_URL}
S3_BUCKET_NAME=${S3_BUCKET_NAME}
S3_OBJECT_PREFIX=${S3_OBJECT_PREFIX}
S3_BASE_URL=${S3_BASE_URL}
AWS_REGION=${AWS_REGION}
BCRYPT_ROUNDS=${BCRYPT_ROUNDS}
WEB_PUSH_VAPID_PUBLIC_KEY=${WEB_PUSH_VAPID_PUBLIC_KEY}
WEB_PUSH_SUBJECT=${WEB_PUSH_SUBJECT}
EOF

cat > "${TMP_DIR}/k8s/base/config/db-secrets.env" <<EOF
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
DB_PASSWORD=${DB_PASSWORD}
EOF

cat > "${TMP_DIR}/k8s/base/config/app-secrets.env" <<EOF
UPLOAD_INTERNAL_TOKEN=${UPLOAD_INTERNAL_TOKEN}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID_VALUE}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY_VALUE}
AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN_VALUE}
WEB_PUSH_VAPID_PRIVATE_KEY=${WEB_PUSH_VAPID_PRIVATE_KEY}
EOF

find "${TMP_DIR}/k8s/overlays/${OVERLAY}" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 | while IFS= read -r -d '' file; do
  perl -0pi -e "s#__BE_IMAGE__#${BE_IMAGE//\//\\/}#g; s#__FE_IMAGE__#${FE_IMAGE//\//\\/}#g; s#__DB_IMAGE__#${DB_IMAGE//\//\\/}#g" "${file}"
done

export KUBECONFIG="${KUBECONFIG_PATH}"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

if [[ "${OVERLAY}" == "k3s-bluegreen" ]]; then
  delete_if_exists "${NAMESPACE}" \
    deployment/community-be \
    deployment/community-fe
else
  delete_if_exists "${NAMESPACE}" \
    deployment/community-be-blue \
    deployment/community-be-green \
    deployment/community-fe-blue \
    deployment/community-fe-green
fi

ECR_PASSWORD="$(aws ecr get-login-password --region "${AWS_REGION}")"
kubectl -n "${NAMESPACE}" create secret docker-registry community-ecr-pull \
  --docker-server="${REGISTRY}" \
  --docker-username="AWS" \
  --docker-password="${ECR_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" delete job community-be-migrate --ignore-not-found --wait=true >/dev/null 2>&1 || true
kubectl apply -k "${TMP_DIR}/k8s/overlays/${OVERLAY}" --namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" rollout status deploy/community-db --timeout=300s
kubectl -n "${NAMESPACE}" rollout status deploy/community-redis --timeout=300s
kubectl -n "${NAMESPACE}" wait --for=condition=complete job/community-be-migrate --timeout=300s

if [[ "${OVERLAY}" == "k3s-rolling" ]]; then
  kubectl -n "${NAMESPACE}" rollout status deploy/community-be --timeout=300s
  kubectl -n "${NAMESPACE}" rollout status deploy/community-fe --timeout=300s
else
  kubectl -n "${NAMESPACE}" rollout status deploy/community-be-blue --timeout=300s
  kubectl -n "${NAMESPACE}" rollout status deploy/community-be-green --timeout=300s
  kubectl -n "${NAMESPACE}" rollout status deploy/community-fe-blue --timeout=300s
  kubectl -n "${NAMESPACE}" rollout status deploy/community-fe-green --timeout=300s
fi

echo
echo "[PASS] k3s overlay 배포 완료"
echo "Overlay    : ${OVERLAY}"
echo "Namespace  : ${NAMESPACE}"
echo "BE image   : ${BE_IMAGE}"
echo "FE image   : ${FE_IMAGE}"
echo "DB image   : ${DB_IMAGE}"
kubectl -n "${NAMESPACE}" get ingress,svc,pods
