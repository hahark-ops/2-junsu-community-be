# AWS One-Shot Infra (Terraform) 가이드

이 폴더는 다음 과제 요구 리소스를 코드로 생성합니다.

- VPC
- IAM
- Security Group
- Elastic IP
- EC2 (FE/BE)
- EFS
- CloudTrail
- CloudWatch
- RDS
- S3
- API Gateway
- Lambda
- ELB(ALB)

업로드는 `API Gateway + Lambda` 경로를 기본으로 구성하고,
Athena 조회는 `API Gateway + Lambda + Athena` 경로를 제공합니다.

## 1) 준비물
- Terraform 설치
- AWS CLI 설치 + 로그인
- EC2 Key Pair 이름
- SSH 허용할 내 공인 IP(CIDR, 예: `1.2.3.4/32`)

## 2) 최초 1회 설정
프로젝트 루트(`/Users/junsu/Desktop/2-junsu-community-be`)에서:

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

`infra/terraform/terraform.tfvars`를 열고 아래는 꼭 수정하세요.

- `admin_cidr`
- `key_pair_name`
- `db_password`

주의:
- `admin_cidr="0.0.0.0/0"`는 `terraform validate`에서 차단됩니다.
- `enable_rds` 기본값은 `false`입니다. RDS가 필요한 경우에만 `true`로 명시하세요.
- `enable_rds=false`로 운영할 때 ECS/Lambda 경로는 `db_host_override`를 함께 지정해야 합니다.
- `upload_allowed_origin`은 단일 Origin만 허용하며 `"*"`는 `terraform validate`에서 차단됩니다.
- `minimal_cost_mode=true`가 기본값이며, NAT/ALB/EFS/CloudTrail은 명시적으로 opt-in 해야 생성됩니다.
- `assign_eip=false`가 기본값입니다. 공인 IP 고정이 필요할 때만 `assign_eip=true`를 명시하세요.

원격 backend를 사용할 경우:

```bash
cp infra/terraform/backend.tf.example infra/terraform/backend.tf
cp infra/terraform/backend.hcl.example infra/terraform/backend.hcl
```

- `backend.hcl`에는 실제 S3 bucket/key를 채웁니다.
- `scripts/infra_apply.sh`, `scripts/infra_plan.sh`, `scripts/infra_destroy.sh`, `scripts/infra_outputs.sh`는 `backend.tf`가 있을 때 `backend.hcl`을 자동 감지합니다.
- `backend.tf`만 있고 `backend.hcl`이 없으면 스크립트는 즉시 실패합니다.
- 예외적으로 로컬 state가 필요할 때만 `TF_FORCE_LOCAL_BACKEND=true`를 명시합니다.

권장:
- `project_name`
- `environment`

## 3) 생성 전 미리보기 (plan)
```bash
./scripts/infra_plan.sh
```

## 4) 실제 생성 (apply)
```bash
./scripts/infra_apply.sh
```

## 5) 생성 결과 확인
```bash
./scripts/infra_outputs.sh
```

중요 출력:
- `alb_dns_name`
- `fe_public_ip`
- `be_public_ip`
- `be_private_ip`
- `rds_endpoint`
- `upload_api_route_url`
- `analytics_api_route_url`
- `upload_bucket_name`
- `athena_workgroup_name`
- `athena_results_bucket_name`

백엔드 `.env`에도 아래를 반영하세요:

```env
UPLOAD_PROVIDER=lambda
UPLOAD_LAMBDA_API_URL=<upload_api_route_url>
```

## 6) 업로드 API 사용 방식
보안 기본 정책:
- API Gateway 업로드 Lambda는 내부 토큰(`X-Upload-Internal-Token`)이 없는 요청을 차단합니다.
- 업로드 URL 발급은 **인증된 BE 경유**(`POST /v1/files/upload-url`)만 허용합니다.
- 업로드 Lambda CORS는 `upload_allowed_origin` 단일 값으로만 응답합니다.

즉, 브라우저/외부에서 API Gateway 업로드 경로를 직접 호출하는 방식은 기본 차단됩니다.

## 7) FE -> API Gateway -> Lambda -> Athena 검증
Athena 경로 URL:

```bash
./scripts/infra_outputs.sh
# analytics_api_route_url 확인
```

호출 테스트:

```bash
./scripts/test_athena_via_apigw.sh <analytics_api_route_url>
```

정상 응답이면 `source: athena` 와 `queryExecutionId`가 포함됩니다.

FE에서 직접 호출 예시:

```javascript
const ATHENA_API_URL = "https://xxxx.execute-api.ap-northeast-2.amazonaws.com/v1/analytics/health";
const resp = await fetch(ATHENA_API_URL);
const data = await resp.json();
console.log(data);
```

## 8) 비용 주의
기본값은 `minimal_cost_mode=true`이며, 이 경우 NAT/ALB/EFS/CloudTrail은 기본 생성되지 않습니다.

비용이 크게 늘어나는 대표 리소스:
- RDS (`enable_rds=true`)
- ALB (`enable_alb=true` 또는 `enable_ecs=true`)
- NAT Gateway (`enable_nat_gateway=true`)
- EFS (`enable_efs=true`)
- CloudTrail (`enable_cloudtrail=true`)
- EIP (`assign_eip=true`)

실습 종료 후 반드시 제거:

```bash
./scripts/infra_destroy.sh
```

## 9) 자주 하는 실수
- `admin_cidr=0.0.0.0/0`로 설정(현재 validate 단계에서 차단)
- `terraform.tfvars`를 git에 커밋 (비밀번호 노출)
- 콘솔에서 리소스 수동 수정 후 Terraform 재적용 시 충돌

## 10) 실무/취업 관점
- **둘 다 중요**합니다.
- 초반: 콘솔로 직접 만들며 개념 이해 (네트워크/권한 감각)
- 실무: Terraform/IaC로 재현성과 변경 이력 관리
- 포트폴리오에는
  - 콘솔 아키텍처 캡처 1장
  - Terraform 코드 저장소 1개
  - 배포/롤백/삭제 절차 문서
  를 함께 제시하면 가장 좋습니다.
