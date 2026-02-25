#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.reverse-proxy.yml"
ENV_FILE="${1:-${ROOT_DIR}/deploy.proxy.env}"
DEFAULT_CONF="${ROOT_DIR}/docker/nginx/conf.d/default.conf"
HTTPS_TEMPLATE="${ROOT_DIR}/docker/nginx/conf.d/https.template.conf"
LE_DIR="${ROOT_DIR}/docker/nginx/letsencrypt"
ACME_DIR="${ROOT_DIR}/docker/nginx/acme"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "배포 env 파일이 없습니다: ${ENV_FILE}"
  echo "예시 생성:"
  echo "  cp ${ROOT_DIR}/deploy.proxy.env.example ${ROOT_DIR}/deploy.proxy.env"
  exit 1
fi

if [[ ! -f "${HTTPS_TEMPLATE}" ]]; then
  echo "HTTPS 템플릿 파일이 없습니다: ${HTTPS_TEMPLATE}"
  exit 1
fi

read_env() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n1 | cut -d'=' -f2- || true)"
  value="${value%$'\r'}"
  echo "${value}"
}

DOMAIN="${DOMAIN:-$(read_env DOMAIN)}"
EMAIL="${EMAIL:-$(read_env EMAIL)}"

if [[ -z "${DOMAIN}" || -z "${EMAIL}" ]]; then
  echo "DOMAIN/EMAIL 값이 필요합니다."
  echo "방법 1) ${ENV_FILE}에 DOMAIN, EMAIL 추가"
  echo "방법 2) DOMAIN=... EMAIL=... scripts/enable_https_domain.sh"
  exit 1
fi

mkdir -p "${LE_DIR}" "${ACME_DIR}"

cd "${ROOT_DIR}"

echo "==> HTTP nginx 먼저 실행 (ACME 챌린지 경로 활성화)"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d nginx

echo "==> certbot 인증서 발급 (${DOMAIN})"
docker run --rm \
  -v "${LE_DIR}:/etc/letsencrypt" \
  -v "${ACME_DIR}:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  --email "${EMAIL}" \
  -d "${DOMAIN}" \
  --agree-tos --no-eff-email --non-interactive \
  --keep-until-expiring

if [[ ! -f "${LE_DIR}/live/${DOMAIN}/fullchain.pem" ]]; then
  echo "인증서 발급 결과를 찾지 못했습니다: ${LE_DIR}/live/${DOMAIN}/fullchain.pem"
  exit 1
fi

echo "==> HTTPS nginx 설정 반영"
sed "s|__DOMAIN__|${DOMAIN}|g" "${HTTPS_TEMPLATE}" > "${DEFAULT_CONF}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d nginx
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T nginx nginx -t
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" restart nginx

echo
echo "HTTPS 적용 완료"
echo "URL: https://${DOMAIN}"
