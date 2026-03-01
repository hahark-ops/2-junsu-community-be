# 커뮤니티 프로젝트 보고서 초안 (노션 제출용)

최종 업데이트: 2026-03-01 (KST)

## 0. 문서 목적

- 본 문서는 커뮤니티 프로젝트의 현재 운영 구조(As-Is)와 고가용성 목표 구조(To-Be)를 비교해 정리한다.
- 범위는 인프라/안정성 설계 중심이며, 기능 설명은 최소화한다.

## 1. 시스템 아키텍처 설계도

### 1.1 As-Is (현재)

- 클라이언트: Browser
- FE: Nginx + 정적 FE 컨테이너
- BE: FastAPI 컨테이너
- DB: MySQL 컨테이너 (EC2 단일 reverse-proxy 경로 기준)
- 파일 업로드:
  - 기본: API Gateway -> Lambda -> S3 (Presigned URL)
  - 폴백: BE `/v1/files/upload`
- 부가 서비스:
  - CloudWatch/CloudTrail
  - API Gateway + Lambda(analytics, upload)

### 1.2 To-Be (목표)

- 다중 AZ + ALB + Auto Scaling Group(EC2) 또는 ECS 서비스 이중화
- DB: RDS Multi-AZ + 자동 백업 + 스냅샷 정책
- 업로드: API Gateway + Lambda + S3 단일 경로로 표준화
- 관측: CloudWatch 대시보드/알람 + 중앙 로그

### 1.3 서비스 흐름

1. 사용자 요청 -> Nginx(80) -> FE 정적 파일 응답
2. API 요청 -> Nginx 리버스 프록시 -> BE API
3. 이미지 업로드:
   - FE -> API Gateway(`/v1/files/upload-url`) -> Lambda -> S3 Presigned URL
   - FE -> S3 직접 PUT
4. 분석 호출:
   - FE/운영도구 -> API Gateway(`/v1/analytics/health`) -> Lambda -> Athena

## 2. 예상 트래픽 기반 장애 시나리오

### 2.1 가정

- 이벤트성 트래픽 급증으로 평시 대비 5~10배 요청 증가
- 읽기 요청(게시글/댓글)이 쓰기 요청보다 훨씬 많음

### 2.2 병목 후보

1. DB 커넥션 고갈
2. BE 컨테이너 CPU/메모리 포화
3. 단일 EC2 네트워크 대역폭 한계
4. 이미지 업로드 시 API/Lambda timeout

### 2.3 장애 전파

1. DB 지연 -> BE 응답 지연/타임아웃
2. BE 지연 -> FE 사용자 체감 장애 확산
3. 인증 API 지연 -> 전체 보호 API 사용 불가

## 3. 고가용성 구현 방안 (AWS 중심)

### 3.1 AZ 분산

- 퍼블릭/프라이빗 서브넷을 2개 AZ에 분산
- BE 워크로드를 최소 2개 인스턴스로 운영

### 3.2 트래픽 분산

- ALB를 단일 진입점으로 사용
- 헬스체크 실패 인스턴스 자동 제외

### 3.3 데이터 이중화/백업

- RDS Multi-AZ + 자동 백업
- S3 버전닝 + 라이프사이클
- 주기적 스냅샷 및 복구 리허설

### 3.4 복구 전략

- RTO 목표: 30분 이내
- RPO 목표: 5분 이내(트랜잭션/백업 정책 기준)
- 롤백:
  - EC2: 이전 이미지 태그 재배포
  - ECS: 이전 task definition 롤백
  - Lambda: alias 이전 버전 롤백

## 4. 과제별 실행 증빙 링크

### 4.1 과제 8 (CI/CD + ECS/Lambda 배포 경험)

- CI 성공: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22476517881`
- EC2 자동배포 성공: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22476551001`
- Lambda 배포 성공: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22469395475`
- ECS 배포 성공: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22469758970`

### 4.2 과제 9 (Terraform destroy/apply)

- 로컬 증빙 폴더:
  - `/Users/junsu/Desktop/2-junsu-community-be/evidence/assignment9-20260301-204358`
- 핵심 로그:
  - `11-destroy-final.txt`
  - `20-apply-final.txt`
  - `21-output-after.txt`
  - `22-state-after-apply.txt`

### 4.3 과제 10/11 증빙

- 과제 10 (테스트코드 -> CI 게이트)
  - CI 실패 run: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544406601`
  - 실패 SHA(`9d03e4f...`)에서는 `deploy-ec2` 미트리거 확인
- 과제 11 (GitHub Actions -> EC2 자동배포)
  - CI 성공 run: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544670598`
  - 배포 성공 run: `https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544690983`
  - EC2 내부 헬스: `curl http://127.0.0.1/` -> `HTTP/1.1 200 OK`

## 5. 운영상 한계와 다음 단계

### 5.1 현재 한계

1. 단일 EC2 경로는 장애 내성이 낮음
2. 컨테이너 DB는 운영 안정성이 낮아 장기 운영 부적합
3. 비용 통제를 위해 상시 운영을 제한 중

### 5.2 다음 단계

1. 과제 12: Jenkins 연동(EC2 Jenkins 또는 GitHub Actions + Jenkins 혼합)
2. CI/CD 운영 분기 정리(main/prod, develop/dev)
3. 비용 최소화 운영(run 후 stop 자동화)
