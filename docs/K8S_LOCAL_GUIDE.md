# Docker Desktop Kubernetes 로컬 배포 가이드

## 1) 사전 조건
- Docker Desktop 실행
- Docker Desktop > Settings > Kubernetes 활성화
- `kubectl cluster-info` 정상
- 로컬 이미지 준비
  - `community-be:local`
  - `community-fe:local`
  - `community-db:local`

참고:
- 로컬 레지스트리 태그만 있는 경우(`localhost:5001/community-*:local`)도 `/Users/junsu/Desktop/2-junsu-community-be/scripts/k8s_up_local.sh`가 자동으로 `community-*:local` 태그로 변환합니다.
- K8s 자산은 `/Users/junsu/Desktop/2-junsu-community-be/k8s/kustomization.yaml` 기준으로 `kubectl apply -k` 한 번에 배포됩니다.
- 민감값은 `Secret`으로 분리되어 있고, `ConfigMap`에는 비민감 설정만 들어갑니다.
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/config/db-secrets.env`, `/Users/junsu/Desktop/2-junsu-community-be/k8s/config/app-secrets.env`는 로컬 재현용 더미 값입니다. 실제 키/비밀번호가 필요하면 복사본에서 덮어써 사용합니다.

## 2) 선언식 구성
주요 파일:
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/kustomization.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/community-workloads.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/config/app.env`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/config/db-secrets.env`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/config/app-secrets.env`

검증:
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
kubectl kustomize k8s >/tmp/community-k8s-rendered.yaml
```

## 3) 배포
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k8s_up_local.sh
```

옵션 예시:
```bash
NAMESPACE=community-local \
PORT_FORWARD_PORT=30080 \
BE_IMAGE=community-be:local \
FE_IMAGE=community-fe:local \
DB_IMAGE=community-db:local \
./scripts/k8s_up_local.sh
```

## 4) 접속
공식 접근 경로는 `NodePort`가 아니라 `kubectl port-forward` 입니다.

기본 경로:
- 앱: `http://127.0.0.1:30080`
- Swagger: `http://127.0.0.1:30080/docs`

수동으로 다시 포워드하려면:
```bash
kubectl -n community-local port-forward svc/community-nginx 30080:80
```

## 5) 스모크 테스트
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' ./scripts/k8s_qa_local.sh
```

`k8s_qa_local.sh`는 기본 URL이 열려 있지 않으면 `svc/community-nginx`에 포트포워드를 다시 붙인 뒤 `/Users/junsu/Desktop/2-junsu-community-be/scripts/qa_ec2_smoke.sh`를 실행합니다.

## 6) 리소스 확인
```bash
kubectl -n community-local get pods,svc,pvc
kubectl -n community-local logs deploy/community-be --tail=100
kubectl -n community-local logs deploy/community-nginx --tail=100
```

## 7) 종료
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k8s_down_local.sh
```

`k8s_down_local.sh`는 저장된 포트포워드 PID를 먼저 정리한 뒤 namespace를 삭제합니다.
