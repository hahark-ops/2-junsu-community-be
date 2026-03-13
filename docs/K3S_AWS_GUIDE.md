# EC2 + k3s 과제 1·2·3 가이드

## 1) 목적
- 과제 1: EC2 단일 노드 `k3s`에 커뮤니티 프로젝트를 Kubernetes 배포하고 Rolling Update 검증
- 과제 2: Rolling Update + Blue/Green 전환을 실제 부하 중 검증
- 과제 3: 두 개의 독립 `k3s` 클러스터에 동일 앱 배포 증빙

## 2) 전제 조건
- AWS CLI 인증 완료
- 대상 EC2가 `running` + SSM `Online`
- ECR 저장소 사용 가능
  - `community-be`
  - `community-fe`
  - `community-db`
- FE 저장소가 로컬에 존재
  - `/Users/junsu/Desktop/2-junsu-community-fe`

## 3) 주요 경로
- AWS k3s rolling overlay
  - `/Users/junsu/Desktop/2-junsu-community-be/k8s/overlays/k3s-rolling`
- AWS k3s blue/green overlay
  - `/Users/junsu/Desktop/2-junsu-community-be/k8s/overlays/k3s-bluegreen`
- k3s bootstrap
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_bootstrap_ec2.sh`
- kubeconfig 회수
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_fetch_kubeconfig.sh`
- 원격 deploy env 회수
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_export_remote_env.sh`
- overlay 배포
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_deploy.sh`
- smoke
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_smoke.sh`
- blue/green 전환
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_bluegreen_switch.sh`
- 부하 테스트
  - `/Users/junsu/Desktop/2-junsu-community-be/scripts/k3s_load_test.sh`

## 4) 과제 1: 단일 k3s 클러스터 + Rolling Update
### 4-1. k3s 설치
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k3s_bootstrap_ec2.sh <BE_INSTANCE_ID>
```

### 4-2. kubeconfig 회수
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
KUBECONFIG_PATH="$(./scripts/k3s_fetch_kubeconfig.sh <BE_INSTANCE_ID>)"
export KUBECONFIG="${KUBECONFIG_PATH}"
```

### 4-3. rolling overlay 배포
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
INSTANCE_ID=<BE_INSTANCE_ID> \
REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com \
TAG=rolling-$(date +%Y%m%d-%H%M%S) \
OVERLAY=k3s-rolling \
CORS_ALLOW_ORIGINS_OVERRIDE=http://<BE_PUBLIC_IP> \
./scripts/k3s_deploy.sh
```

### 4-4. 확인
```bash
kubectl -n community-k3s get pods,svc,ingress
BASE_URL=http://<BE_PUBLIC_IP> ./scripts/k3s_smoke.sh
```

### 4-5. Rolling Update 검증
새 태그로 같은 명령을 다시 실행하고 아래를 확인합니다.
- `community-be`, `community-fe`가 `replicas: 2`로 교체됨
- `maxUnavailable: 0`, `maxSurge: 1`로 서비스 응답이 유지됨
- `kubectl rollout status deploy/community-be -n community-k3s`
- `kubectl rollout status deploy/community-fe -n community-k3s`

### 4-6. 실제 검증 결과
- 검증 일시: `2026-03-13`
- 클러스터 A
  - 인스턴스: `i-03b2d60bda8fdcfaa`
  - Public IP: `13.125.228.204`
- smoke 결과:
  - `[PASS] 기본 k3s smoke 완료: http://13.125.228.204`

## 5) 과제 2: Blue/Green + 부하 테스트
### 5-1. blue/green overlay 배포
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
INSTANCE_ID=<BE_INSTANCE_ID> \
REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com \
TAG=bluegreen-$(date +%Y%m%d-%H%M%S) \
OVERLAY=k3s-bluegreen \
CORS_ALLOW_ORIGINS_OVERRIDE=http://<BE_PUBLIC_IP> \
./scripts/k3s_deploy.sh
```

### 5-2. 부하 테스트
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
BASE_URL=http://<BE_PUBLIC_IP> ./scripts/k3s_load_test.sh
```

### 5-3. Blue/Green 전환
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
export KUBECONFIG=<kubeconfig-path>
NAMESPACE=community-k3s ./scripts/k3s_bluegreen_switch.sh green
BASE_URL=http://<BE_PUBLIC_IP> ./scripts/k3s_load_test.sh
```

전환 후 다시 blue로 돌리는 예시:
```bash
NAMESPACE=community-k3s ./scripts/k3s_bluegreen_switch.sh blue
```

### 5-4. acceptance
- k6 결과에서 `http_req_failed`가 급격히 증가하지 않을 것
- p95 latency가 비정상적으로 붕괴하지 않을 것
- 전환 중 `/`, `/login.html`, `/v1/posts`가 계속 응답할 것

### 5-5. 실제 검증 결과
- 검증 일시: `2026-03-13`
- Rolling Update + k6
  - 대상: `http://13.125.228.204`
  - 결과: `p95 34.86ms`
  - 실패율: `0.31%`
- Blue/Green + k6
  - 대상: `http://13.125.228.204`
  - 결과: `p95 56.78ms`
  - 실패율: `0.00%`
- Blue/Green 전환 직후 즉시 응답 확인 결과도 모두 `200`

## 6) 과제 3: 멀티 클러스터 증빙
### 6-1. 클러스터 구성
- 클러스터 A
  - 기존 BE EC2 1대에 `k3s`
- 클러스터 B
  - 기존 FE EC2 또는 추가 EC2 1대에 `k3s`

### 6-2. 클러스터 B bootstrap
```bash
cd /Users/junsu/Desktop/2-junsu-community-be
./scripts/k3s_bootstrap_ec2.sh <CLUSTER_B_INSTANCE_ID>
```

### 6-3. 클러스터 A/B 각각 배포
클러스터 A:
```bash
KUBECONFIG_A="$(./scripts/k3s_fetch_kubeconfig.sh <CLUSTER_A_INSTANCE_ID>)"
KUBECONFIG_PATH="${KUBECONFIG_A}" \
INSTANCE_ID=<CLUSTER_A_INSTANCE_ID> \
REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com \
TAG=multicluster-a-$(date +%Y%m%d-%H%M%S) \
OVERLAY=k3s-rolling \
CORS_ALLOW_ORIGINS_OVERRIDE=http://<CLUSTER_A_PUBLIC_IP> \
./scripts/k3s_deploy.sh
```

클러스터 B:
```bash
KUBECONFIG_B="$(./scripts/k3s_fetch_kubeconfig.sh <CLUSTER_B_INSTANCE_ID>)"
KUBECONFIG_PATH="${KUBECONFIG_B}" \
INSTANCE_ID=<CLUSTER_B_INSTANCE_ID> \
REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com \
TAG=multicluster-b-$(date +%Y%m%d-%H%M%S) \
OVERLAY=k3s-rolling \
CORS_ALLOW_ORIGINS_OVERRIDE=http://<CLUSTER_B_PUBLIC_IP> \
./scripts/k3s_deploy.sh
```

### 6-4. smoke
```bash
BASE_URL=http://<CLUSTER_A_PUBLIC_IP> ./scripts/k3s_smoke.sh
BASE_URL=http://<CLUSTER_B_PUBLIC_IP> ./scripts/k3s_smoke.sh
```

과제 3의 범위는 여기까지입니다.
- 두 개의 독립 클러스터에 동일 앱 배포
- 각 public IP에서 각각 동작 확인

이번 가이드는 아래 항목을 포함하지 않습니다.
- 글로벌 DNS 전환
- 자동 failover
- 클러스터 간 데이터 동기화

### 6-5. 실제 검증 결과
- 검증 일시: `2026-03-13`
- 클러스터 A
  - 인스턴스: `i-03b2d60bda8fdcfaa`
  - Public IP: `13.125.228.204`
- 클러스터 B
  - 인스턴스: `i-0198391f9b166a573`
  - Public IP: `43.202.40.115`
- 두 public IP 모두 `./scripts/k3s_smoke.sh` 통과
- 클러스터 B는 `scripts/migrations/20260312_add_dm_realtime_published.sql`를 idempotent하게 수정한 뒤 재배포해 migration job까지 통과시켰습니다.

## 7) 비용 통제
- 검증이 끝나면 EC2는 바로 `stop`
- k3s와 앱 리소스를 남겨둘 필요가 없으면 인스턴스 자체를 중지

## 8) 주의 사항
- k3s는 Traefik Ingress를 사용하므로 기존 Docker Compose 앱이 포트 `80`을 점유하면 먼저 내려야 합니다.
- `k3s_bootstrap_ec2.sh`는 기존 `docker-compose.reverse-proxy.yml` 기반 앱을 우선 정리한 뒤 k3s를 설치합니다.
- 수동 배포는 ECR 태그와 kubeconfig, `deploy.proxy.env` 값에 의존하므로, 인스턴스의 `/opt/2-junsu-community-be/deploy.proxy.env`가 최신 상태인지 확인해야 합니다.
