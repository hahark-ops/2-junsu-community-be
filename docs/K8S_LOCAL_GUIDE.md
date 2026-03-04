# Docker Desktop Kubernetes 로컬 배포 가이드

## 1) 사전 조건
- Docker Desktop 실행
- Docker Desktop > Settings > Kubernetes 활성화
- `kubectl cluster-info` 정상
- 로컬 이미지 준비
  - `community-be:local`
  - `community-fe:local`
  - `community-db:local`

로컬 레지스트리 태그만 있는 경우(`localhost:5001/community-*:local`)도 `scripts/k8s_up_local.sh`가 자동으로 로컬 태그로 변환합니다.

## 2) 배포
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k8s_up_local.sh
```

옵션 예시:
```bash
NAMESPACE=community-local \
NODE_PORT=30080 \
BE_IMAGE=community-be:local \
FE_IMAGE=community-fe:local \
DB_IMAGE=community-db:local \
./scripts/k8s_up_local.sh
```

## 3) 접속
- 앱: `http://127.0.0.1:30080`
- Swagger: `http://127.0.0.1:30080/docs`

## 4) 스모크 테스트
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' ./scripts/k8s_qa_local.sh
```

## 5) 리소스 확인
```bash
kubectl -n community-local get pods,svc,pvc
kubectl -n community-local logs deploy/community-be --tail=100
```

## 6) 종료
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k8s_down_local.sh
```
