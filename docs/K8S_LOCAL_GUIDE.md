# Docker Desktop Kubernetes 로컬 배포 가이드

## 1) 사전 조건
- Docker Desktop 실행
- Docker Desktop > Settings > Kubernetes 활성화
- `kubectl cluster-info` 정상
- 로컬 이미지 준비
  - `community-be:local`
  - `community-fe:local`
  - `community-db:local`
  - Redis는 `redis:7-alpine`를 Kubernetes가 직접 pull 합니다.

참고:
- 로컬 레지스트리 태그만 있는 경우(`localhost:5001/community-*:local`)도 `/Users/junsu/Desktop/2-junsu-community-be/scripts/k8s_up_local.sh`가 자동으로 `community-*:local` 태그로 변환합니다.
- K8s 자산은 두 계층으로 나뉩니다.
  - 기본 실행: `/Users/junsu/Desktop/2-junsu-community-be/k8s/base`
  - DM 분산 증빙: `/Users/junsu/Desktop/2-junsu-community-be/k8s/overlays/dm-scale-proof`
  - 루트 `/Users/junsu/Desktop/2-junsu-community-be/k8s/kustomization.yaml`은 `base`를 가리킵니다.
- 민감값은 `Secret`으로 분리되어 있고, `ConfigMap`에는 비민감 설정만 들어갑니다.
- `k8s/base/kustomization.yaml`의 기본 namespace는 `community-local`입니다.
- `NAMESPACE=... ./scripts/k8s_up_local.sh`로 실행하면 스크립트가 임시 kustomization에 target namespace를 강제로 다시 써서 apply합니다.
- 실제 secret 원본 파일은 Git에 포함하지 않습니다. `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/db-secrets.env.example`, `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/app-secrets.env.example`만 추적합니다.
- `kubectl apply -k /Users/junsu/Desktop/2-junsu-community-be/k8s/base`는 실제 secret 파일이 있어야만 동작합니다. `.example` 값은 직접 참조하지 않습니다.

## 2) 선언식 구성
주요 파일:
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/kustomization.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/community-workloads.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/community-migrate-job.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/app.env`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/db-secrets.env.example`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/app-secrets.env.example`
- `/Users/junsu/Desktop/2-junsu-community-be/k8s/overlays/dm-scale-proof/kustomization.yaml`
- `/Users/junsu/Desktop/2-junsu-community-be/scripts/k8s_dm_multi_pod_proof.sh`

검증:
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
kubectl kustomize k8s/base >/tmp/community-k8s-base-rendered.yaml
kubectl kustomize k8s/overlays/dm-scale-proof >/tmp/community-k8s-dm-proof-rendered.yaml
```

## 3) Secret 파일 준비
처음 실행 전 한 번은 example 파일을 복사하고 값을 수정해야 합니다.

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
cp k8s/base/config/db-secrets.env.example k8s/base/config/db-secrets.env
cp k8s/base/config/app-secrets.env.example k8s/base/config/app-secrets.env
```

수정 대상:
- `k8s/base/config/db-secrets.env`
  - `MYSQL_ROOT_PASSWORD`
  - `DB_PASSWORD`
- `k8s/base/config/app-secrets.env`
  - `UPLOAD_INTERNAL_TOKEN`
  - 필요 시 `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
  - `WEB_PUSH_VAPID_PRIVATE_KEY`
- `k8s/base/config/app.env`
  - `WEB_PUSH_VAPID_PUBLIC_KEY`
  - `WEB_PUSH_SUBJECT`

주의:
- `change_me_*` placeholder가 남아 있으면 `/Users/junsu/Desktop/2-junsu-community-be/scripts/k8s_up_local.sh`는 apply 전에 실패합니다.
- secret 파일이 없으면 스크립트가 example에서 자동 복사한 뒤 즉시 종료합니다. 이 경우 값을 수정한 후 다시 실행해야 합니다.

## 4) 배포
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
K8S_TARGET=base ./scripts/k8s_up_local.sh
```

옵션 예시:
```bash
NAMESPACE=community-local \
K8S_TARGET=base \
PORT_FORWARD_PORT=30080 \
BE_IMAGE=community-be:local \
FE_IMAGE=community-fe:local \
DB_IMAGE=community-db:local \
./scripts/k8s_up_local.sh
```

DM 분산 증빙 overlay:
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
K8S_TARGET=dm-scale-proof ./scripts/k8s_up_local.sh
```

namespace 동작:
- 기본 namespace: `community-local`
- 커스텀 namespace 예시:

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
NAMESPACE=community-dev ./scripts/k8s_up_local.sh
```

- 스크립트는 선택한 Kustomize 경로(`base` 또는 `overlays/dm-scale-proof`)를 해당 namespace에 적용합니다.

## 5) 접속
공식 접근 경로는 `NodePort`가 아니라 `kubectl port-forward` 입니다.

기본 경로:
- 앱: `http://127.0.0.1:30080`
- Swagger: `http://127.0.0.1:30080/docs`

수동으로 다시 포워드하려면:
```bash
kubectl -n community-local port-forward svc/community-nginx 30080:80
```

## 6) 스모크 테스트
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
QA_EMAIL='<qa_email>' QA_PASSWORD='<qa_password>' ./scripts/k8s_qa_local.sh
```

`k8s_qa_local.sh`는 기본 URL이 열려 있지 않으면 `svc/community-nginx`에 포트포워드를 다시 붙인 뒤 `/Users/junsu/Desktop/2-junsu-community-be/scripts/qa_ec2_smoke.sh`를 실행합니다.

## 7) DM 분산 증빙 (Redis + 2 Pods)
과제 2용으로는 `K8S_TARGET=dm-scale-proof`에서 base 스택의 Redis를 그대로 사용하고, `community-be` Pod만 2개로 늘려 서로 다른 WebSocket 서버 역할을 맡게 합니다.

```bash
cd /Users/junsu/Desktop/2-junsu-community-be
K8S_TARGET=dm-scale-proof ./scripts/k8s_up_local.sh
./scripts/k8s_dm_multi_pod_proof.sh
```

스크립트 동작:
- `community-be` Pod 2개와 `community-redis` rollout 확인
- Pod A / Pod B IP를 고정 추출
- Pod A 내부에서 Python 클라이언트를 실행해
  - 사용자 2명 생성/로그인
  - Pod A, Pod B에 각각 직접 WebSocket 연결
  - A -> B 메시지 전달
  - B 읽음 이벤트가 A로 돌아오는지 확인

성공 시 예시 출력:
```json
{"roomId":12,"podA":"community-be-xxxx","podB":"community-be-yyyy","messageContent":"redis-proof-...","receiverIsMine":false,"senderIsMine":true,"readEventType":"messages_read","roomAUnread":0,"roomBUnread":0}
```

## 8) 리소스 확인
```bash
kubectl -n community-local get pods,svc,pvc
kubectl -n community-local logs deploy/community-be --tail=100
kubectl -n community-local logs deploy/community-redis --tail=100
kubectl -n community-local logs deploy/community-nginx --tail=100
```

## 9) 종료
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k8s_down_local.sh
```

`k8s_down_local.sh`는 저장된 포트포워드 PID를 먼저 정리한 뒤 namespace를 삭제합니다.
