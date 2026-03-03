#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."
TF_DIR="${ROOT_DIR}/infra/terraform"
TFVARS_FILE="${TFVARS_FILE:-${TF_DIR}/terraform.tfvars}"

AWS_REGION="${AWS_REGION:-ap-northeast-2}"

has_tfvars=false
if [[ -f "${TFVARS_FILE}" ]]; then
  has_tfvars=true
fi

read_tfvar() {
  local key="$1"
  if [[ "${has_tfvars}" != "true" ]]; then
    return 0
  fi

  local raw
  raw="$(grep -E "^${key}[[:space:]]*=" "${TFVARS_FILE}" | head -n1 | cut -d'=' -f2- || true)"
  raw="$(echo "${raw}" | sed -E 's/^[[:space:]]*//; s/[[:space:]]*$//; s/^"//; s/"$//')"
  echo "${raw}"
}

tf_output_raw() {
  local key="$1"
  if [[ ! -d "${TF_DIR}" ]] || ! command -v terraform >/dev/null 2>&1; then
    return 0
  fi
  if terraform -chdir="${TF_DIR}" output -raw "${key}" >/dev/null 2>&1; then
    terraform -chdir="${TF_DIR}" output -raw "${key}"
  fi
}

PROJECT_NAME="${PROJECT_NAME:-$(read_tfvar project_name)}"
ENVIRONMENT="${ENVIRONMENT:-$(read_tfvar environment)}"
DB_NAME="${DB_NAME:-$(read_tfvar db_name)}"
DB_USER="${DB_USER:-$(read_tfvar db_username)}"
DB_PASSWORD="${DB_PASSWORD:-$(read_tfvar db_password)}"

PROJECT_NAME="${PROJECT_NAME:-community}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
DB_NAME="${DB_NAME:-community_db}"
DB_USER="${DB_USER:-community_user}"

if [[ -z "${DB_PASSWORD}" ]]; then
  echo "DB_PASSWORD 가 필요합니다. (env 또는 terraform.tfvars)"
  exit 1
fi

NAME_PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-${FUNCTION_NAME:-${NAME_PREFIX}-be-api}}"
API_NAME="${API_NAME:-${NAME_PREFIX}-be-http-api}"
ECR_REPO="${ECR_REPO:-${NAME_PREFIX}-be-lambda}"
ROLE_NAME="${ROLE_NAME:-${NAME_PREFIX}-be-lambda-role}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "${AWS_REGION}")"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

RDS_ENDPOINT="${RDS_ENDPOINT:-${RDS_HOST:-${DB_HOST:-$(tf_output_raw rds_endpoint)}}}"
RDS_PORT="${RDS_PORT:-${DB_PORT:-$(tf_output_raw rds_port)}}"
UPLOAD_LAMBDA_API_URL="${UPLOAD_LAMBDA_API_URL:-$(tf_output_raw upload_api_route_url)}"
UPLOAD_INTERNAL_TOKEN="${UPLOAD_INTERNAL_TOKEN:-}"
FE_PUBLIC_IP="${FE_PUBLIC_IP:-$(tf_output_raw fe_public_ip)}"
ALB_DNS_NAME="${ALB_DNS_NAME:-$(tf_output_raw alb_dns_name)}"
VPC_ID="${VPC_ID:-$(tf_output_raw vpc_id)}"

if [[ -z "${UPLOAD_INTERNAL_TOKEN}" ]]; then
  UPLOAD_HANDLER_FUNCTION_NAME="${UPLOAD_HANDLER_FUNCTION_NAME:-${NAME_PREFIX}-upload-handler}"
  UPLOAD_INTERNAL_TOKEN="$(aws lambda get-function-configuration \
    --region "${AWS_REGION}" \
    --function-name "${UPLOAD_HANDLER_FUNCTION_NAME}" \
    --query 'Environment.Variables.UPLOAD_INTERNAL_TOKEN' \
    --output text 2>/dev/null || true)"
  if [[ "${UPLOAD_INTERNAL_TOKEN}" == "None" ]]; then
    UPLOAD_INTERNAL_TOKEN=""
  fi
fi

if [[ -z "${RDS_ENDPOINT}" || -z "${RDS_PORT}" || -z "${VPC_ID}" || -z "${UPLOAD_LAMBDA_API_URL}" || -z "${UPLOAD_INTERNAL_TOKEN}" ]]; then
  echo "필수 값이 부족합니다. 아래 값들을 env로 지정하거나 terraform output이 필요합니다."
  echo "- RDS_ENDPOINT (또는 DB_HOST)"
  echo "- RDS_PORT (또는 DB_PORT)"
  echo "- VPC_ID"
  echo "- UPLOAD_LAMBDA_API_URL"
  echo "- UPLOAD_INTERNAL_TOKEN (또는 업로드 Lambda 환경변수에서 자동 조회 가능)"
  exit 1
fi

CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-}"
if [[ -z "${CORS_ALLOW_ORIGINS}" ]]; then
  origins=()
  if [[ -n "${FE_PUBLIC_IP}" ]]; then
    origins+=("http://${FE_PUBLIC_IP}:3000")
  fi
  if [[ -n "${ALB_DNS_NAME}" ]]; then
    origins+=("http://${ALB_DNS_NAME}")
  fi
  if [[ ${#origins[@]} -gt 0 ]]; then
    CORS_ALLOW_ORIGINS="$(IFS=,; echo "${origins[*]}")"
  else
    echo "CORS_ALLOW_ORIGINS를 계산할 수 없습니다. env로 명시하세요."
    exit 1
  fi
fi

BE_SG_ID="${BE_SG_ID:-}"
if [[ -z "${BE_SG_ID}" ]]; then
  BE_SG_ID="$(aws ec2 describe-security-groups \
    --region "${AWS_REGION}" \
    --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Name,Values=${NAME_PREFIX}-be-sg" \
    --query 'SecurityGroups[0].GroupId' --output text)"
fi

if [[ -z "${BE_SG_ID}" || "${BE_SG_ID}" == "None" ]]; then
  echo "BE_SG_ID를 찾지 못했습니다. env로 지정하거나 보안그룹 태그를 확인하세요."
  exit 1
fi

SUBNET_IDS="${SUBNET_IDS:-}"
if [[ -z "${SUBNET_IDS}" ]]; then
  SUBNET_IDS="$(aws ec2 describe-subnets \
    --region "${AWS_REGION}" \
    --filters "Name=vpc-id,Values=${VPC_ID}" "Name=tag:Tier,Values=private" \
    --query 'Subnets[].SubnetId' --output text | tr '\t' ',')"
fi

if [[ -z "${SUBNET_IDS}" ]]; then
  echo "SUBNET_IDS를 찾지 못했습니다. env로 comma 형식 지정 필요"
  exit 1
fi

echo "==> ECR 리포지토리 준비: ${ECR_REPO}"
aws ecr describe-repositories --region "${AWS_REGION}" --repository-names "${ECR_REPO}" >/dev/null 2>&1 \
  || aws ecr create-repository --region "${AWS_REGION}" --repository-name "${ECR_REPO}" >/dev/null

echo "==> Docker 빌드/푸시"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

cd "${ROOT_DIR}"
if docker buildx version >/dev/null 2>&1; then
  docker buildx build \
    --platform linux/amd64 \
    --provenance=false \
    --sbom=false \
    -f Dockerfile.lambda \
    -t "${IMAGE_URI}" \
    --push .
else
  docker build -f Dockerfile.lambda -t "${IMAGE_URI}" .
  docker push "${IMAGE_URI}"
fi

echo "==> IAM Role 준비: ${ROLE_NAME}"
if ! aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  TRUST_FILE="$(mktemp)"
  cat > "${TRUST_FILE}" <<'EOF'
{
  "Version":"2012-10-17",
  "Statement":[
    {
      "Effect":"Allow",
      "Principal":{"Service":"lambda.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }
  ]
}
EOF
  aws iam create-role --role-name "${ROLE_NAME}" --assume-role-policy-document "file://${TRUST_FILE}" >/dev/null
  rm -f "${TRUST_FILE}"
fi

aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null || true
aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole >/dev/null || true

ROLE_ARN="$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)"

ENV_FILE="$(mktemp)"
cat > "${ENV_FILE}" <<EOF
{
  "Variables": {
    "DB_HOST": "${RDS_ENDPOINT}",
    "DB_PORT": "${RDS_PORT}",
    "DB_USER": "${DB_USER}",
    "DB_PASSWORD": "${DB_PASSWORD}",
    "DB_NAME": "${DB_NAME}",
    "CORS_ALLOW_ORIGINS": "${CORS_ALLOW_ORIGINS}",
    "COOKIE_SAMESITE": "lax",
    "COOKIE_SECURE": "false",
    "UPLOAD_PROVIDER": "lambda",
    "UPLOAD_LAMBDA_API_URL": "${UPLOAD_LAMBDA_API_URL}",
    "UPLOAD_INTERNAL_TOKEN": "${UPLOAD_INTERNAL_TOKEN}",
    "PYTHONUNBUFFERED": "1"
  }
}
EOF

echo "==> Lambda 함수 배포: ${FUNCTION_NAME}"
if aws lambda get-function --region "${AWS_REGION}" --function-name "${FUNCTION_NAME}" >/dev/null 2>&1; then
  aws lambda update-function-code \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}" \
    --image-uri "${IMAGE_URI}" >/dev/null

  aws lambda wait function-updated \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}"

  aws lambda update-function-configuration \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}" \
    --role "${ROLE_ARN}" \
    --timeout 30 \
    --memory-size 1024 \
    --vpc-config "SubnetIds=${SUBNET_IDS},SecurityGroupIds=${BE_SG_ID}" \
    --environment "file://${ENV_FILE}" >/dev/null

  aws lambda wait function-updated \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}"
else
  aws lambda create-function \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}" \
    --package-type Image \
    --code "ImageUri=${IMAGE_URI}" \
    --role "${ROLE_ARN}" \
    --timeout 30 \
    --memory-size 1024 \
    --vpc-config "SubnetIds=${SUBNET_IDS},SecurityGroupIds=${BE_SG_ID}" \
    --environment "file://${ENV_FILE}" >/dev/null

  aws lambda wait function-active-v2 \
    --region "${AWS_REGION}" \
    --function-name "${FUNCTION_NAME}"
fi

rm -f "${ENV_FILE}"

echo "==> API Gateway 준비: ${API_NAME}"
API_ID="$(aws apigatewayv2 get-apis --region "${AWS_REGION}" --query "Items[?Name=='${API_NAME}'].ApiId | [0]" --output text)"

if [[ -z "${API_ID}" || "${API_ID}" == "None" ]]; then
  API_ID="$(aws apigatewayv2 create-api \
    --region "${AWS_REGION}" \
    --name "${API_NAME}" \
    --protocol-type HTTP \
    --cors-configuration "AllowOrigins=${CORS_ALLOW_ORIGINS},AllowMethods=GET,POST,PUT,PATCH,DELETE,OPTIONS,AllowHeaders=*" \
    --query 'ApiId' --output text)"
fi

LAMBDA_INVOKE_ARN="$(aws lambda get-function --region "${AWS_REGION}" --function-name "${FUNCTION_NAME}" --query 'Configuration.FunctionArn' --output text)"

INTEGRATION_ID="$(aws apigatewayv2 create-integration \
  --region "${AWS_REGION}" \
  --api-id "${API_ID}" \
  --integration-type AWS_PROXY \
  --integration-uri "${LAMBDA_INVOKE_ARN}" \
  --payload-format-version '2.0' \
  --timeout-in-millis 30000 \
  --query 'IntegrationId' --output text)"

ROUTE_TARGET="integrations/${INTEGRATION_ID}"

aws apigatewayv2 create-route --region "${AWS_REGION}" --api-id "${API_ID}" --route-key 'ANY /{proxy+}' --target "${ROUTE_TARGET}" >/dev/null 2>&1 || \
aws apigatewayv2 update-route --region "${AWS_REGION}" --api-id "${API_ID}" --route-id "$(aws apigatewayv2 get-routes --region "${AWS_REGION}" --api-id "${API_ID}" --query "Items[?RouteKey=='ANY /{proxy+}'].RouteId | [0]" --output text)" --target "${ROUTE_TARGET}" >/dev/null

aws apigatewayv2 create-route --region "${AWS_REGION}" --api-id "${API_ID}" --route-key 'ANY /' --target "${ROUTE_TARGET}" >/dev/null 2>&1 || \
aws apigatewayv2 update-route --region "${AWS_REGION}" --api-id "${API_ID}" --route-id "$(aws apigatewayv2 get-routes --region "${AWS_REGION}" --api-id "${API_ID}" --query "Items[?RouteKey=='ANY /'].RouteId | [0]" --output text)" --target "${ROUTE_TARGET}" >/dev/null

aws apigatewayv2 create-stage --region "${AWS_REGION}" --api-id "${API_ID}" --stage-name '$default' --auto-deploy >/dev/null 2>&1 || true

STATEMENT_ID="AllowInvokeFromApiGw-${API_ID}"
aws lambda add-permission \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --statement-id "${STATEMENT_ID}" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*/*" >/dev/null 2>&1 || true

API_ENDPOINT="$(aws apigatewayv2 get-api --region "${AWS_REGION}" --api-id "${API_ID}" --query 'ApiEndpoint' --output text)"

echo
echo "배포 완료"
echo "FUNCTION_NAME=${FUNCTION_NAME}"
echo "API_ENDPOINT=${API_ENDPOINT}"
echo "HEALTH_URL=${API_ENDPOINT}/"
echo "DOCS_URL=${API_ENDPOINT}/docs"
