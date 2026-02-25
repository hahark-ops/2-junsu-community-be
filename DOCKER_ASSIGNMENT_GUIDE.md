# Docker 과제 실행 가이드 (Nginx + FE + BE + DB)

이 가이드는 아래 과제 요구사항을 그대로 수행하기 위한 실행 순서입니다.

1. FE/BE/DB 이미지화 + `docker-compose` 로컬 실행/테스트  
2. 이미지 레지스트리 푸시  
3. Linux 서버에서 이미지 기반 배포
4. Nginx 리버스 프록시 단일 진입점 구성

## 0) 준비

- 폴더 위치(중요)
  - BE: `/Users/junsu/Desktop/2-junsu-community-be`
  - FE: `/Users/junsu/Desktop/2-junsu-community-fe`
- Docker Desktop 실행

## 1) 로컬 실행/테스트

### 1-1. 구성 파일

- BE Dockerfile: `/Users/junsu/Desktop/2-junsu-community-be/Dockerfile`
- FE Dockerfile: `/Users/junsu/Desktop/2-junsu-community-be/docker/fe.Dockerfile`
- DB Dockerfile: `/Users/junsu/Desktop/2-junsu-community-be/docker/db.Dockerfile`
- 로컬 compose: `/Users/junsu/Desktop/2-junsu-community-be/docker-compose.yml`
- 로컬 env: `/Users/junsu/Desktop/2-junsu-community-be/.env.docker`

### 1-2. 실행

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/compose_up_local.sh
```

### 1-3. 테스트

```bash
# APP 진입(nginx -> fe)
curl -i http://127.0.0.1/

# BE 문서(nginx -> be)
curl -i http://127.0.0.1/docs

# 프록시 경유 API 체크(실패가 정상: 계정 없음)
curl -i -X POST http://127.0.0.1/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"none@example.com","password":"Password!123"}'
```

### 1-4. 종료

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/compose_down_local.sh
```

## 2) 레지스트리 푸시

### 2-1. Docker Hub 예시

```bash
docker login

cd /Users/junsu/Desktop/2-junsu-community-be
REGISTRY=docker.io/<dockerhub_id> TAG=v1 ./scripts/push_images.sh
```

푸시 결과 이미지:

- `docker.io/<dockerhub_id>/community-fe:v1`
- `docker.io/<dockerhub_id>/community-be:v1`
- `docker.io/<dockerhub_id>/community-db:v1`

### 2-2. ECR 예시

`REGISTRY`를 ECR 주소로 지정하면 동일 스크립트 사용 가능:

```bash
REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com TAG=v1 ./scripts/push_images.sh
```

## 3) Linux 배포 (이미지 기반)

### 3-1. 서버 준비

Linux 서버에 Docker + Docker Compose plugin 설치 후, BE 프로젝트 폴더를 배치합니다.

### 3-2. 배포 env 생성

```bash
cd /opt/2-junsu-community-be
cp deploy.env.example deploy.env
```

`/opt/2-junsu-community-be/deploy.env` 값 수정:

- `BE_IMAGE`
- `FE_IMAGE`
- `DB_IMAGE`
- `MYSQL_ROOT_PASSWORD`
- `DB_PASSWORD`
- `CORS_ALLOW_ORIGINS`

### 3-3. 실행

```bash
cd /opt/2-junsu-community-be
./scripts/deploy_with_images.sh ./deploy.env
```

### 3-4. 검증

```bash
docker compose --env-file deploy.env -f docker-compose.deploy.yml ps
curl -i http://127.0.0.1:3000/
curl -i http://127.0.0.1:8000/
```

## 참고

- 기본 설정은 과제 실습용 로컬 구성(`UPLOAD_PROVIDER=local`)입니다.
- Mac(M1/M2)에서 Linux 배포용 이미지를 만들 때는 `linux/amd64` 플랫폼 빌드를 권장합니다.
- `scripts/push_images.sh` 는 `buildx`가 있으면 자동으로 `--platform linux/amd64` 기반 푸시를 사용합니다.
