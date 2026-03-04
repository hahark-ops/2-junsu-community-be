# 커뮤니티 백엔드 프로젝트 코드 검수 보고서

> **최종 검수 일시**: 2026-03-04 11:27 KST  
> **대상 저장소**: `hahark-ops/2-junsu-community-be`  
> **최신 커밋**: `9d78612` (문서: 보고서·CI/CD 가이드·진행내역 최신화)  
> **검수 범위**: 전체 코드, 인프라, CI/CD, 문서

---

## 1. 프로젝트 개요

FastAPI 기반 커뮤니티 REST API 백엔드 프로젝트.

| 항목 | 내용 |
|---|---|
| 언어/프레임워크 | Python 3.11 / FastAPI |
| DB | MySQL 8 (Docker 컨테이너, 커넥션 풀링) |
| 인증 | 세션 쿠키 기반 (DB 세션 + bcrypt 해싱) |
| 파일 업로드 | Local / S3 / Lambda(Presigned URL) 3중 프로바이더 |
| 컨테이너 | Docker Compose (local / deploy / reverse-proxy / portainer) |
| CI/CD | GitHub Actions (CI 3단계 → EC2 자동배포 + ECS/Lambda 배포) |
| IaC | Terraform (VPC/ALB/EC2/ECS/RDS/Lambda/S3/CloudTrail/Athena) |
| 모니터링 | CloudWatch 알람 (CPU 80% 임계치) |

### 프로젝트 구조

```
├── main.py                    # FastAPI 앱 엔트리포인트
├── database.py                # MySQL 커넥션 풀 관리
├── dependencies.py            # 인증 DI (get_current_user)
├── utils.py                   # 유틸리티 (검증, 해싱, APIException)
├── schema.sql                 # DB 스키마 (5개 테이블)
├── routers/                   # API 라우터 (6개)
│   ├── index.py, auth.py, post.py, comment.py, user.py, file.py
├── controllers/               # 비즈니스 로직 (4개)
│   ├── auth.py, post.py, comment.py, user.py
├── models/                    # DB 접근 계층 (5개)
│   ├── auth_model.py, post_model.py, comment_model.py, user_model.py, common.py
├── .github/workflows/         # CI/CD (4개 워크플로우)
│   ├── ci.yml, deploy-ec2.yml, deploy-ecs.yml, deploy-lambda.yml
├── infra/terraform/           # Terraform IaC (1327줄)
├── scripts/                   # 운영 스크립트 (17개)
├── docker-compose*.yml        # Docker Compose (4종)
├── Dockerfile, Dockerfile.lambda
└── docs/                      # 프로젝트 문서
```

---

## 2. 검수 결과 — 잘 구현된 부분

### 2.1 코드 아키텍처

- **3계층 분리** (Router → Controller → Model) 일관되게 적용
- **공통 DB 커서 관리** — `models/common.py`의 `get_cursor` 컨텍스트 매니저로 커넥션 획득/반환 일원화
- **일관된 에러 응답** — 모든 API가 `{ code, message, data }` 포맷 사용
- **커스텀 예외 클래스** — `APIException` + 글로벌 핸들러로 FastAPI 기본 에러와 분리
- **글로벌 예외 로깅** — `logger.exception(...)` 으로 method/path/query/client_host 기록 (클라이언트 응답은 내부 정보 미노출)
- **SQL 동적 필드 화이트리스트** — `ALLOWED_POST_UPDATE_FIELDS`, `ALLOWED_USER_UPDATE_FIELDS` 상수로 허용 컬럼 제한, 위반 시 `ValueError` → `APIException(400)` 변환

### 2.2 인증 & 보안

- **bcrypt 해싱** — 라운드 수 환경변수 설정 가능 (4~16 범위 제한)
- **세션 쿠키 보안** — `httponly`, `secure`, `samesite`, `domain` 모두 환경변수로 제어
- **서버 간 인증** — BE→Lambda 업로드 요청에 `UPLOAD_INTERNAL_TOKEN` 헤더 검증
- **입력 검증** — 이메일/비밀번호/닉네임 정규식 기반 체계적 검증
- **파일 업로드 이중 검증** — BE와 Lambda 양측에서 확장자 + Content-Type 검증

### 2.3 DB 설계

- **FK 관계 + CASCADE** — `users` → `posts/comments/likes/sessions` 연쇄 삭제
- **좋아요 중복 방지** — `UNIQUE KEY (postId, userEmail)`
- **세션 만료 인덱스** — `idx_sessions_expiresAt`로 조회 성능 최적화
- **닉네임 변경 시 동기화** — 게시글/댓글의 `writer` 필드를 트랜잭션 내에서 일괄 업데이트

### 2.4 파일 업로드

- **3가지 프로바이더** — `local` / `s3` / `lambda` 환경변수로 전환
- **Presigned URL 발급 엔드포인트** — `POST /v1/files/upload-url` (Pydantic 모델 적용)
- **업로드 타입별 크기 제한 분리** — profile / post 각각 별도 제한
- **스트리밍 방식 크기 검증** — 1MB 청크 단위로 읽으며 제한 초과 시 즉시 거부

### 2.5 Docker & 배포

- **4종 Compose 구성** — `local` / `deploy` / `reverse-proxy` / `portainer`
- **Healthcheck 적용** — DB 컨테이너 `mysqladmin ping` + `service_healthy` 의존성
- **Lambda 컨테이너 이미지** — `Dockerfile.lambda`로 별도 빌드
- **Portainer HTTPS** — `mkcert` 기반 자체 서명 인증서 + Private Registry 인증

### 2.6 CI/CD 파이프라인

- **CI 3단계** — `python-compile` → `compose-config` → `smoke-test`
- **EC2 자동배포** — CI 성공 시 SSM 기반 원격 배포 (워크플로우 체인)
- **자동 롤백** — SSM Parameter Store에 마지막 성공 태그 저장, 실패 시 이전 태그로 복원
- **비용 통제** — push 자동배포 시 EC2 자동기동 금지 (`EC2_AUTO_START=false`), 수동 dispatch에서만 허용
- **OIDC 인증** — AWS 크레덴셜에 IAM Role OIDC 사용 (장기 키 미보관)
- **동일 태그 재배포** — `redeploy_same_tag_ec2.sh`로 보안 패치 등 빠른 재배포 지원
- **배포 시 시크릿 검증** — `MODE=deploy`에서 placeholder/기본 비밀번호 사용 시 즉시 실패 (배포/롤백 양쪽 적용)

### 2.7 Terraform 인프라

- **VPC** — 2AZ × 퍼블릭/프라이빗 서브넷, NAT Gateway
- **ALB** — FE/BE/ECS 타겟그룹, 헬스체크
- **Security Group 분리** — ALB / FE / BE / RDS / ECS / EFS 각각 별도
- **선택적 리소스** — `enable_rds`, `enable_ecs` 플래그로 비용 제어
- **Lambda** — upload(Presigned URL) + analytics(Athena) 2종
- **CloudWatch 알람** — FE/BE EC2 CPU 80% 임계치 알람
- **일관된 태깅** — `common_tags` (Project/Environment/ManagedBy) 전역 적용

### 2.8 운영 스크립트 & 문서

- **env 자동 보정** — `ensure_deploy_proxy_env.sh`로 누락 키 기본값 채움
- **QA 자동화** — `qa_ec2_smoke.sh`, `qa_local_additional.sh`로 배포 후 검증
- **마이그레이션** — `run_migrations.sh`로 Compose 환경별 DB 스키마 적용
- **문서** — 보고서 초안(277줄), 시스템 아키텍처(Mermaid), CICD 계획, 과제 증빙 링크

---

## 3. 검수 결과 — 개선 제안

### 3.1 코드 품질 (Minor)

| # | 항목 | 파일 | 상태 | 설명 |
|---|---|---|---|---|
| 1 | `_resolve_upload_dir` 중복 | `main.py:71`, `routers/file.py:19` | 잔여 | 동일 함수가 두 곳에 존재. 한 곳에서 import하는 방식으로 통합 권장 |
| 2 | `profileimage` vs `profileImage` | 컨트롤러 전반 | 잔여 | DB 컬럼(`profileimage`)과 API 응답(`profileImage`)의 케이스 불일치 |
| 3 | ~~`pyproject.toml` 의존성 누락~~ | `pyproject.toml` | ✅ 해결 | `boto3>=1.34.0`, `mangum>=0.17.0` 추가 완료 |
| 4 | ~~만료 세션 정리~~ | `models/auth_model.py` | ✅ 해결 | `purge_expired_sessions(limit=500)` 추가, 인증 조회 전에 만료 세션 정리 수행 |
| 5 | ~~글로벌 500 에러 로깅~~ | `main.py:50-58` | ✅ 해결 | `logger.exception(...)` 으로 method/path/query/client_host 기록 추가 |

### 3.2 보안 (Medium)

| # | 항목 | 파일 | 상태 | 설명 |
|---|---|---|---|---|
| 6 | ~~SQL key injection 경로~~ | `models/post_model.py`, `models/user_model.py` | ✅ 해결 | `ALLOWED_POST_UPDATE_FIELDS`, `ALLOWED_USER_UPDATE_FIELDS` 화이트리스트 + `ValueError` + `APIException(400)` |
| 7 | ~~평문 비밀번호 호환 코드~~ | `utils.py:62` | ✅ 해결 | `verify_password`에서 평문 fallback 제거, 비해시 값은 즉시 인증 실패 |
| 8 | ~~Lambda CORS 와일드카드~~ | `infra/terraform/lambda/index.js:26` | ✅ 해결 | `ALLOWED_ORIGIN` 단일 Origin 사용, Terraform에서 `upload_allowed_origin`에 `"*"` 차단 validation 추가 |

### 3.3 인프라 / 운영 (Minor)

| # | 항목 | 상태 | 설명 |
|---|---|---|---|
| 9 | Terraform state 로컬 관리 | 잔여 | S3+DynamoDB remote backend 전환 권장 |
| 10 | `deploy-ec2.yml` 복잡도 | 잔여 | 462줄 — composite action으로 공통 부분 분리 고려 |
| 11 | ~~`local/portainer/` gitignore 누락~~ | ✅ 해결 | `.gitignore`에 `local/portainer/` 반영 완료 |

---

## 4. 종합 평가

| 영역 | 점수 | 비고 |
|---|---|---|
| 코드 구조 & 계층 분리 | ★★★★☆ | 3계층 일관 분리, Pydantic 부분 적용 시작 |
| DB 설계 & 쿼리 | ★★★★☆ | FK/CASCADE/INDEX 적절, 만료 세션 정리 로직 반영 |
| 인증 & 보안 | ★★★★★ | bcrypt + 세션 쿠키 + internal token + SQL 화이트리스트 |
| Docker & 컨테이너 | ★★★★★ | 4종 Compose, Healthcheck, Portainer |
| CI/CD 파이프라인 | ★★★★★ | 3단계 CI, 자동배포, 자동롤백, 비용 통제, 시크릿 fail-fast |
| Terraform 인프라 | ★★★★★ | VPC/ALB/EC2/ECS/Lambda/S3/CloudWatch 1327줄 |
| 파일 업로드 | ★★★★★ | 3종 프로바이더, Presigned URL, 이중 검증 |
| 운영 스크립트 & 자동화 | ★★★★★ | 17개 스크립트, env 자동 보정, QA 자동화 |
| 문서화 | ★★★★★ | 보고서/아키텍처/증빙/가이드 체계적 |
| 테스트 / QA | ★★★★☆ | CI smoke test + QA 스크립트 (단위 테스트 부재) |

### 이전 검수 대비 해결 현황

| 상태 | 건수 | 항목 |
|---|---|---|
| ✅ 해결 | 8건 | SQL 화이트리스트 검증, 글로벌 500 에러 로깅, pyproject.toml 의존성 정합성, 배포 env 시크릿 fail-fast, 만료 세션 정리, 평문 비밀번호 fallback 제거, Lambda CORS 단일 Origin 강제, `local/portainer/` gitignore 반영 |
| 잔여 | 4건 | `_resolve_upload_dir` 중복, profileimage 케이스 혼용, tfstate 로컬, deploy-ec2 복잡도 |

### 결론

> 학습 과제로서 **매우 높은 완성도**의 프로젝트입니다. 검수 지적 항목 중 **보안/운영 핵심 8건이 해결**되었고, 현재 잔여 항목은 4건(구조/운영 개선 성격)입니다. 특히 SQL 화이트리스트 검증, 배포 시 시크릿 검증(`MODE=deploy` fail-fast), 평문 비밀번호 fallback 제거, Lambda CORS 단일 Origin 강제는 운영 안정성을 의미 있게 높였습니다.
