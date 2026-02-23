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
`POST {upload_api_route_url}` 는 `multipart/form-data` 업로드입니다.

- form field: `file` (바이너리 파일)
- form field: `type` (`profile` 또는 `post`)

검증 스크립트:

```bash
./scripts/test_upload_via_apigw.sh <upload_api_route_url> ./sample.png profile
```

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
RDS/ALB/NAT(없음)/EIP 등은 비용이 발생합니다.
실습 종료 후 반드시 제거:

```bash
./scripts/infra_destroy.sh
```

## 9) 자주 하는 실수
- `admin_cidr=0.0.0.0/0`로 장기간 운영
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
