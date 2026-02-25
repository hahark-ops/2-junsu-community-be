# Nginx 리버스 프록시 미니퀘스트 가이드

## 목표
1. 단일 EC2에서 Docker로 `nginx + fe + be + mysql` 동작
2. `nginx`가 `/`는 FE로, `/v1`는 BE로 라우팅
3. 도메인 + HTTPS(Let's Encrypt) 적용

## 준비
1. EC2(리눅스)에 Docker 설치
2. 저장소 클론
3. `deploy.proxy.env` 생성

```bash
cd /opt/2-junsu-community-be
cp deploy.proxy.env.example deploy.proxy.env
```

## 1) 리버스 프록시(HTTP) 기동
`deploy.proxy.env`의 최소값을 먼저 채웁니다.

- `BE_IMAGE`, `FE_IMAGE`, `DB_IMAGE`
- `MYSQL_ROOT_PASSWORD`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `CORS_ALLOW_ORIGINS` (예: `http://<EC2_PUBLIC_IP>`)

기동:

```bash
./scripts/proxy_up_single_ec2.sh
```

접속:

- `http://<EC2_PUBLIC_IP>`

## 2) HTTPS + 도메인 적용
### 2-1. DNS 설정
도메인 DNS에 A 레코드 추가:

- `@` -> `<EC2_PUBLIC_IP>`
- `www` -> `<EC2_PUBLIC_IP>` (선택)

### 2-2. env 값 추가
`deploy.proxy.env`에 아래 값 추가:

```env
DOMAIN=your-domain.com
EMAIL=you@example.com
```

HTTPS 적용:

```bash
./scripts/enable_https_domain.sh
```

완료 후 접속:

- `https://your-domain.com`

## 보안그룹 권장
외부 인바운드:

- `80/tcp` 허용
- `443/tcp` 허용
- `22/tcp`는 본인 IP만 허용

차단 권장:

- `3000`, `8000`, `3306` 외부 차단 (내부 컨테이너 통신만 사용)

## 파일 설명
- `docker-compose.reverse-proxy.yml`: 단일 EC2 배포용 Compose
- `docker/nginx/conf.d/default.conf`: HTTP 리버스 프록시 설정
- `docker/nginx/conf.d/https.template.conf`: HTTPS 템플릿
- `scripts/proxy_up_single_ec2.sh`: HTTP 배포
- `scripts/enable_https_domain.sh`: HTTPS 인증서 발급/반영
