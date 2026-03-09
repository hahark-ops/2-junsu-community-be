# CI/CD 실행 가이드 (과제 8)

최종 업데이트: 2026-03-04 (KST)

## 1. 운영 기준

- 단일 EC2 리버스 프록시 배포를 기본 경로로 사용
- AWS 인증은 GitHub OIDC AssumeRole 고정
- 이미지 레지스트리는 ECR 통일
- `main/develop` push -> `ci` 성공 시 `deploy-ec2` 자동 실행
- `workflow_dispatch` 수동 배포도 유지
- ECS/Lambda는 과제 8 증빙용 수동 실행 경로로 유지
- QA 후 기본 정책은 `stop`
- EC2가 `stopped` 상태면 `deploy-ec2`는 자동 기동 없이 실패 처리(비용 통제)

## 2. 워크플로우 파일

- `/Users/junsu/Desktop/2-junsu-community-be/.github/workflows/ci.yml`
- `/Users/junsu/Desktop/2-junsu-community-be/.github/workflows/deploy-ec2.yml`
- `/Users/junsu/Desktop/2-junsu-community-be/.github/workflows/deploy-ecs.yml`
- `/Users/junsu/Desktop/2-junsu-community-be/.github/workflows/deploy-lambda.yml`

## 3. 워크플로우별 동작

## 3.1 `ci.yml`

- 트리거: `push/pull_request` (`main`, `develop`)
- 검증:
  - Python compile check
  - `docker-compose.yml` config check (FE cross-repo checkout 포함)
  - `docker-compose.reverse-proxy.yml` config check
  - 로컬 compose 기동 + `qa_ec2_smoke.sh` 스모크 테스트

## 3.2 `deploy-ec2.yml`

- 트리거:
  - `workflow_run` (`ci` 성공, push 이벤트, `main/develop`)
  - `workflow_dispatch` (수동)
- 입력:
  - `environment` (`dev|prod`)
  - `image_tag` (옵션)
  - `rollback_on_fail` (기본 `true`)
- 동작:
  1. OIDC 인증
  2. ECR 로그인
  3. 배포 시크릿 precheck(`DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`) fail-fast
  4. GitHub Secrets를 AWS SSM Parameter Store `SecureString`으로 업서트
  5. FE는 `ci` 아티팩트에 기록된 커밋 SHA를 checkout하고, 수동 실행만 `fe_ref`를 사용
  6. BE/FE/DB 이미지 빌드 및 푸시
  7. SSM 원격 명령으로 `deploy.proxy.env` 이미지 태그 갱신
  8. `/opt/2-junsu-community-be/scripts/ensure_deploy_proxy_env.sh`를 `MODE=deploy`로 실행(placeholder 차단)
  9. `/opt/2-junsu-community-be/scripts/proxy_up_single_ec2.sh` 실행
  10. EC2 내부 smoke (`qa_ec2_smoke.sh`) 실행
  11. 마지막 성공 `tag + source_sha`를 SSM Parameter에 저장
  12. 실패 시 이전 성공 `tag + source_sha`로 자동 롤백
  13. `concurrency`로 동일 브랜치 중복 배포 방지

## 3.3 `deploy-ecs.yml`

- 트리거: `workflow_dispatch`
- 전제:
  - Terraform에서 `enable_ecs=true`
- 입력:
  - `environment` (`dev|prod`)
  - `image_tag` (옵션)
  - `keep_running` (기본 `false`)
- 동작:
  1. OIDC 인증 + ECR 푸시
  2. 기존 Task Definition 기반 새 revision 등록
  3. ECS Service update + stable 대기
  4. Target Group health 확인
  5. 실패 시 이전 task definition 롤백
  6. `dev` + `keep_running=false`면 desired count 0으로 조정

## 3.4 `deploy-lambda.yml`

- 트리거: `workflow_dispatch`
- 입력:
  - `environment` (`dev|prod`)
  - `image_tag` (옵션)
- 동작:
  1. OIDC 인증 + ECR 푸시 (`Dockerfile.lambda`)
  2. Lambda image 업데이트
  3. `publish-version` 후 alias(`live`) 전환
  4. `scripts/test_be_lambda_api.sh`로 smoke
  5. 실패 시 alias 이전 버전으로 복귀

## 4. GitHub Secrets

- `AWS_ROLE_ARN_DEV`
- `AWS_ROLE_ARN_PROD`
- `FE_REPO_READ_TOKEN` (FE private repo면 필수)
- `QA_EMAIL_DEV`
- `QA_PASSWORD_DEV`
- `QA_EMAIL_PROD` (선택)
- `QA_PASSWORD_PROD` (선택)

## 5. GitHub Variables

- `AWS_REGION=ap-northeast-2`
- `ECR_REGISTRY=<account>.dkr.ecr.ap-northeast-2.amazonaws.com`
- `ECR_REPO_BE=community-be`
- `ECR_REPO_FE=community-fe`
- `ECR_REPO_DB=community-db`
- `ECR_REPO_BE_LAMBDA=community-be-lambda`
- `FE_REPO=<org>/2-junsu-community-fe` (선택, 미지정 시 owner 기준 자동 계산)
- `EC2_INSTANCE_ID_PROXY_DEV`
- `EC2_INSTANCE_ID_PROXY_PROD`
- `EC2_DEPLOY_DIR=/opt/2-junsu-community-be`
- `SSM_PARAM_LAST_TAG_DEV=/<project>/dev/deploy/last_success_tag`
- `SSM_PARAM_LAST_TAG_PROD=/<project>/prod/deploy/last_success_tag`
- `LAMBDA_FUNCTION_NAME_DEV`
- `LAMBDA_FUNCTION_NAME_PROD`
- `LAMBDA_API_ENDPOINT_DEV`
- `LAMBDA_API_ENDPOINT_PROD`
- `LAMBDA_ALIAS_NAME=live` (선택)
- `ECS_CLUSTER_NAME_DEV`
- `ECS_SERVICE_NAME_DEV`
- `ECS_TASK_FAMILY_DEV`
- `ECS_TARGET_GROUP_ARN_DEV`
- `ECS_CLUSTER_NAME_PROD` (선택)
- `ECS_SERVICE_NAME_PROD` (선택)
- `ECS_TASK_FAMILY_PROD` (선택)
- `ECS_TARGET_GROUP_ARN_PROD` (선택)

## 6. Terraform 연동 포인트

- `/Users/junsu/Desktop/2-junsu-community-be/infra/terraform/variables.tf`
  - `enable_ecs`, `enable_rds` 및 ECS 관련 변수 추가
- `/Users/junsu/Desktop/2-junsu-community-be/infra/terraform/main.tf`
  - ECS Cluster/TaskDefinition/Service/LogGroup/ALB TargetGroup 추가 (옵션)
  - RDS 리소스 옵션화(`enable_rds=false`일 때 미생성)
- `/Users/junsu/Desktop/2-junsu-community-be/infra/terraform/outputs.tf`
  - `ecs_cluster_name`, `ecs_service_name`, `ecs_task_family`, `ecs_target_group_arn` 출력

## 7. 롤백 정책

- EC2: SSM Parameter의 이전 `tag + source_sha`로 env 갱신 후 재배포
- ECS: 이전 task definition으로 service 재배포
- Lambda: alias를 이전 function version으로 되돌림

## 8. 점검 순서

1. `develop/main` push -> `ci.yml` green 확인
2. `ci` 완료 후 `deploy-ec2.yml` 자동 실행/성공 확인
3. `deploy-lambda.yml` dev 배포/alias 롤백 리허설
4. `enable_ecs=true` 후 `deploy-ecs.yml` dev 검증
5. 비용 통제 정책대로 QA 후 stop 적용
