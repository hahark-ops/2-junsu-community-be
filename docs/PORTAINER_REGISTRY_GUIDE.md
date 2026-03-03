# Portainer HTTPS + Private Registry (로컬 추가 과제)

이 가이드는 `/Users/junsu/Desktop/2-junsu-community-be` 기준으로, AWS 없이 로컬에서 아래를 완료하는 절차입니다.

1. Portainer HTTPS 실행
2. Private Registry 구축/인증
3. FE/BE/DB 이미지 push/pull
4. Nginx+FE+BE+MySQL 통합 구동 및 QA

## 1) Portainer + Registry 스택 기동

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
REGISTRY_USER=community REGISTRY_PASSWORD='community123!' ./scripts/setup_portainer_local.sh
```

포트 충돌 시(예: 5000 이미 사용 중):

```bash
REGISTRY_PORT=5001 PORTAINER_HTTPS_PORT=9444 REGISTRY_USER=community REGISTRY_PASSWORD='community123!' ./scripts/setup_portainer_local.sh
```

기대 결과:
- 기본값: Portainer `https://localhost:9443`, Registry `http://localhost:5000/v2/_catalog`
- 포트 변경 시: `PORTAINER_HTTPS_PORT`, `REGISTRY_PORT` 값에 따라 변경

## 2) 로컬 private registry에 이미지 빌드/푸시

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
REGISTRY_HOST=localhost:5000 REGISTRY_USER=community REGISTRY_PASSWORD='community123!' FE_DIR=/Users/junsu/Desktop/2-junsu-community-fe ./scripts/build_and_push_local_registry.sh

# 포트 변경 예시(5001)
REGISTRY_HOST=localhost:5001 REGISTRY_USER=community REGISTRY_PASSWORD='community123!' FE_DIR=/Users/junsu/Desktop/2-junsu-community-fe ./scripts/build_and_push_local_registry.sh
```

기대 결과:
- `localhost:5000/community-be:local`
- `localhost:5000/community-fe:local`
- `localhost:5000/community-db:local`
- push 로그: `/Users/junsu/Desktop/2-junsu-community-be/evidence/additional/03-push-log.txt`

## 3) 앱 스택 실행 (이미지 pull 기반)

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
cp deploy.portainer.local.env.example deploy.portainer.local.env
docker compose --env-file deploy.portainer.local.env -f docker-compose.reverse-proxy.yml up -d
./scripts/run_migrations.sh docker-compose.reverse-proxy.yml deploy.portainer.local.env
```

## 4) 통합 QA

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
QA_EMAIL='<실제_qa_email>' QA_PASSWORD='<실제_qa_password>' ./scripts/qa_local_additional.sh

# 포트 변경 예시(9444/5001)
REGISTRY_HOST=localhost:5001 PORTAINER_HTTPS_PORT=9444 QA_EMAIL='<실제_qa_email>' QA_PASSWORD='<실제_qa_password>' ./scripts/qa_local_additional.sh
```

증빙 파일 저장 경로:
- `/Users/junsu/Desktop/2-junsu-community-be/evidence/additional`

## 5) 종료

앱 스택 종료:

```bash
docker compose --env-file deploy.portainer.local.env -f docker-compose.reverse-proxy.yml down
```

Portainer/Registry 종료:

```bash
docker compose -f docker-compose.portainer.yml down
```

데이터 유지:
- `portainer_data`, `registry_data` 볼륨은 유지됩니다.

## 트러블슈팅

1. `docker login localhost:5000` 실패
- Docker Desktop insecure registry 설정에 `localhost:5000` 추가 후 재시도

2. `listen tcp 0.0.0.0:5000: bind: address already in use`
- 이미 5000 포트를 다른 컨테이너/프로세스가 사용 중입니다.
- `REGISTRY_PORT=5001 PORTAINER_HTTPS_PORT=9444`로 재실행하거나 기존 점유 프로세스를 종료하세요.

3. `mkcert` 없음
- macOS:
  - `brew install mkcert nss`
  - `mkcert -install`

4. Portainer HTTPS 경고
- `mkcert -install`로 로컬 루트 인증서 신뢰를 먼저 적용
