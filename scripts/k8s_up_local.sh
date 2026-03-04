#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKLOAD_FILE="${ROOT_DIR}/k8s/community-workloads.yaml"
NGINX_CONF="${ROOT_DIR}/docker/nginx/conf.d/default.conf"
SCHEMA_FILE="${ROOT_DIR}/schema.sql"

NAMESPACE="${NAMESPACE:-community-local}"
NODE_PORT="${NODE_PORT:-30080}"

BE_IMAGE="${BE_IMAGE:-community-be:local}"
FE_IMAGE="${FE_IMAGE:-community-fe:local}"
DB_IMAGE="${DB_IMAGE:-community-db:local}"

DB_NAME="${DB_NAME:-community_db}"
DB_USER="${DB_USER:-community_user}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
DB_PASSWORD="${DB_PASSWORD:-}"

CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-http://localhost,http://127.0.0.1}"
COOKIE_SECURE="${COOKIE_SECURE:-false}"
COOKIE_SAMESITE="${COOKIE_SAMESITE:-lax}"
COOKIE_MAX_AGE="${COOKIE_MAX_AGE:-604800}"
MAX_UPLOAD_SIZE_BYTES="${MAX_UPLOAD_SIZE_BYTES:-26214400}"
MAX_PROFILE_UPLOAD_SIZE_BYTES="${MAX_PROFILE_UPLOAD_SIZE_BYTES:-26214400}"
MAX_POST_UPLOAD_SIZE_BYTES="${MAX_POST_UPLOAD_SIZE_BYTES:-31457280}"
UPLOAD_PROVIDER="${UPLOAD_PROVIDER:-local}"
UPLOAD_LAMBDA_API_URL="${UPLOAD_LAMBDA_API_URL:-}"
UPLOAD_INTERNAL_TOKEN="${UPLOAD_INTERNAL_TOKEN:-}"
S3_BUCKET_NAME="${S3_BUCKET_NAME:-}"
S3_OBJECT_PREFIX="${S3_OBJECT_PREFIX:-uploads}"
S3_BASE_URL="${S3_BASE_URL:-}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN:-}"
BCRYPT_ROUNDS="${BCRYPT_ROUNDS:-12}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl이 필요합니다. Docker Desktop Kubernetes를 먼저 활성화하세요."
  exit 1
fi

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "Kubernetes 클러스터에 연결할 수 없습니다. Docker Desktop > Kubernetes를 확인하세요."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker 명령을 찾을 수 없습니다."
  exit 1
fi

if [[ ! -f "${WORKLOAD_FILE}" || ! -f "${NGINX_CONF}" || ! -f "${SCHEMA_FILE}" ]]; then
  echo "필수 파일이 없습니다. k8s/community-workloads.yaml, docker/nginx/conf.d/default.conf, schema.sql 을 확인하세요."
  exit 1
fi

if [[ -z "${MYSQL_ROOT_PASSWORD}" ]]; then
  MYSQL_ROOT_PASSWORD="localRoot!$(date +%s)"
  echo "[INFO] MYSQL_ROOT_PASSWORD 미지정 -> 임시 로컬 비밀번호 생성"
fi

if [[ -z "${DB_PASSWORD}" ]]; then
  DB_PASSWORD="localDb!$(date +%s)"
  echo "[INFO] DB_PASSWORD 미지정 -> 임시 로컬 비밀번호 생성"
fi

ensure_image_exists() {
  local target="$1"
  local fallback="$2"

  if docker image inspect "${target}" >/dev/null 2>&1; then
    return 0
  fi

  if docker image inspect "${fallback}" >/dev/null 2>&1; then
    echo "[INFO] 이미지 태그 변환: ${fallback} -> ${target}"
    docker tag "${fallback}" "${target}"
    return 0
  fi

  echo "[ERROR] 로컬 이미지가 없습니다: ${target}"
  echo "        fallback도 없음: ${fallback}"
  echo "        먼저 빌드하세요. 예)"
  echo "        BE: docker build -t community-be:local ."
  echo "        FE: docker build -t community-fe:local /Users/junsu/Desktop/2-junsu-community-fe"
  echo "        DB: docker build -f docker/db.Dockerfile -t community-db:local ."
  exit 1
}

ensure_image_exists "${BE_IMAGE}" "localhost:5001/community-be:local"
ensure_image_exists "${FE_IMAGE}" "localhost:5001/community-fe:local"
ensure_image_exists "${DB_IMAGE}" "localhost:5001/community-db:local"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

kubectl -n "${NAMESPACE}" create secret generic community-db-secret \
  --from-literal=MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD}" \
  --from-literal=DB_PASSWORD="${DB_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create configmap community-schema \
  --from-file=01-schema.sql="${SCHEMA_FILE}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create configmap community-nginx-conf \
  --from-file=default.conf="${NGINX_CONF}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create configmap community-app-config \
  --from-literal=DB_NAME="${DB_NAME}" \
  --from-literal=DB_USER="${DB_USER}" \
  --from-literal=CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS}" \
  --from-literal=COOKIE_SECURE="${COOKIE_SECURE}" \
  --from-literal=COOKIE_SAMESITE="${COOKIE_SAMESITE}" \
  --from-literal=COOKIE_MAX_AGE="${COOKIE_MAX_AGE}" \
  --from-literal=MAX_UPLOAD_SIZE_BYTES="${MAX_UPLOAD_SIZE_BYTES}" \
  --from-literal=MAX_PROFILE_UPLOAD_SIZE_BYTES="${MAX_PROFILE_UPLOAD_SIZE_BYTES}" \
  --from-literal=MAX_POST_UPLOAD_SIZE_BYTES="${MAX_POST_UPLOAD_SIZE_BYTES}" \
  --from-literal=UPLOAD_PROVIDER="${UPLOAD_PROVIDER}" \
  --from-literal=UPLOAD_LAMBDA_API_URL="${UPLOAD_LAMBDA_API_URL}" \
  --from-literal=UPLOAD_INTERNAL_TOKEN="${UPLOAD_INTERNAL_TOKEN}" \
  --from-literal=S3_BUCKET_NAME="${S3_BUCKET_NAME}" \
  --from-literal=S3_OBJECT_PREFIX="${S3_OBJECT_PREFIX}" \
  --from-literal=S3_BASE_URL="${S3_BASE_URL}" \
  --from-literal=AWS_REGION="${AWS_REGION}" \
  --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  --from-literal=AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN}" \
  --from-literal=BCRYPT_ROUNDS="${BCRYPT_ROUNDS}" \
  --dry-run=client -o yaml | kubectl apply -f -

RENDERED="$(mktemp)"
sed \
  -e "s|__NAMESPACE__|${NAMESPACE}|g" \
  -e "s|__BE_IMAGE__|${BE_IMAGE}|g" \
  -e "s|__FE_IMAGE__|${FE_IMAGE}|g" \
  -e "s|__DB_IMAGE__|${DB_IMAGE}|g" \
  -e "s|__NODE_PORT__|${NODE_PORT}|g" \
  "${WORKLOAD_FILE}" > "${RENDERED}"

kubectl apply -f "${RENDERED}"
rm -f "${RENDERED}"

kubectl -n "${NAMESPACE}" rollout status deploy/community-db --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-be --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-fe --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/community-nginx --timeout=240s

echo
echo "[PASS] Kubernetes 로컬 배포 완료"
echo "Namespace : ${NAMESPACE}"
echo "App URL   : http://127.0.0.1:${NODE_PORT}"
echo "Docs URL  : http://127.0.0.1:${NODE_PORT}/docs"
echo
echo "스모크 테스트:"
echo "QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' BASE_URL='http://127.0.0.1:${NODE_PORT}' ${ROOT_DIR}/scripts/qa_ec2_smoke.sh"
