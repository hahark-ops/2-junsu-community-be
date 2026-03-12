# 🌐 아무 말 대잔치 - 커뮤니티 게시판

> 자유롭게 소통하는 커뮤니티 게시판 서비스입니다.

<br>

## 📖 목차

- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [CI/CD (과제 8)](#-cicd-과제-8)
- [추가 과제 (Portainer/Registry)](#-추가-과제-portainerregistry)
- [Kubernetes 로컬 배포 (Docker Desktop)](#-kubernetes-로컬-배포-docker-desktop)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 및 실행](#️-설치-및-실행)
- [페이지 상세](#-페이지-상세)
  - [로그인](#-로그인-loginhtml)
  - [회원가입](#-회원가입-signuphtml)
  - [게시글 목록](#-게시글-목록-indexhtml)
  - [게시글 상세](#-게시글-상세-post_detailhtml)
  - [게시글 작성](#-게시글-작성-post_writehtml)
  - [게시글 수정](#-게시글-수정-post_edithtml)
  - [프로필 관리](#-프로필-관리-profilehtml)
  - [비밀번호 변경](#-비밀번호-변경-passwordhtml)
- [공통 컴포넌트](#-공통-컴포넌트)
- [관련 저장소](#-관련-저장소)

<br>

---

## 🚀 CI/CD (과제 8)

- 워크플로우 위치: `/Users/junsu/Desktop/2-junsu-community-be/.github/workflows`
  - `ci.yml`
  - `deploy-ec2.yml`
  - `deploy-ecs.yml`
  - `deploy-lambda.yml`
- 기준
  - AWS 인증: OIDC AssumeRole
  - 이미지 레지스트리: ECR
  - EC2 배포: 단일 리버스 프록시 + SSM 원격 실행 (기본 운영 경로)
  - 자동 배포: `main/develop` push -> `ci` 성공 시 `deploy-ec2` 자동 실행
  - 동일 태그 재배포: `/Users/junsu/Desktop/2-junsu-community-be/scripts/redeploy_same_tag_ec2.sh`
    - `reuse_existing_images=true`로 기존 ECR 이미지를 그대로 다시 배포
  - CI 게이트: compile/compose 검증 + 로컬 compose 스모크 테스트
  - FE checkout ref: 자동 배포는 `ci`가 기록한 FE 커밋 SHA를 사용, 수동 실행은 `fe_ref`를 반드시 명시
  - 배포 시크릿: GitHub Actions가 SSM payload에 평문을 싣지 않고 AWS SSM Parameter Store `SecureString`에 저장 후 EC2가 직접 조회
  - EC2 롤백: 마지막 성공 `tag + source_sha + fe_sha` 기준
  - CORS: `CORS_ALLOW_ORIGINS_DEV/PROD` GitHub Variables가 필수이며, 없으면 배포가 즉시 실패
  - `ci-metadata/fe-source-sha.txt` 아티팩트가 없으면 자동배포는 실패하며, 브랜치명 fallback을 사용하지 않음
  - 수동 immutable 재배포(`reuse_existing_images=true` + 명시 `image_tag`)는 마지막 성공 포인터를 덮어쓰지 않음
  - ECS/Lambda: 과제 증빙용 수동 실행 경로 유지
  - 실패 시 롤백: EC2 태그 롤백 / ECS task definition 롤백 / Lambda alias 롤백
- 자세한 변수/시크릿/실행 순서:
  - `/Users/junsu/Desktop/2-junsu-community-be/docs/CICD_PLAN.md`

---

## 🧰 추가 과제 (Portainer/Registry)

- 로컬 전용 Portainer + Private Registry 스택
  - Compose: `/Users/junsu/Desktop/2-junsu-community-be/docker-compose.portainer.yml`
  - Portainer(기본): `https://localhost:9443`
  - Registry(기본): `http://localhost:5000`
  - 포트 충돌 시: `PORTAINER_HTTPS_PORT`, `REGISTRY_PORT` 환경변수로 변경 가능
- 자동화 스크립트
  - 초기 셋업: `/Users/junsu/Desktop/2-junsu-community-be/scripts/setup_portainer_local.sh`
  - 이미지 빌드/푸시: `/Users/junsu/Desktop/2-junsu-community-be/scripts/build_and_push_local_registry.sh`
  - 통합 QA: `/Users/junsu/Desktop/2-junsu-community-be/scripts/qa_local_additional.sh`
- 앱 이미지 기반 실행용 env 예시
  - `/Users/junsu/Desktop/2-junsu-community-be/deploy.portainer.local.env.example`
- 상세 가이드
  - `/Users/junsu/Desktop/2-junsu-community-be/docs/PORTAINER_REGISTRY_GUIDE.md`

---

## ☸️ Kubernetes 로컬 배포 (Docker Desktop)

- 선언식 루트
  - 기본 실행: `/Users/junsu/Desktop/2-junsu-community-be/k8s/base`
  - DM 분산 증빙: `/Users/junsu/Desktop/2-junsu-community-be/k8s/overlays/dm-scale-proof`
  - 루트 `/Users/junsu/Desktop/2-junsu-community-be/k8s/kustomization.yaml`은 `base`를 가리킵니다.
- base 스택 구성: `community-be`(1 replica), `community-redis`, `community-fe`, `community-db`, `community-nginx`
- DM 분산 증빙 overlay 구성: base 위에 `community-be`만 2 replicas로 확장하고, 업로드 볼륨을 `emptyDir`로 바꿉니다.
- secret 파일은 `.example`만 Git에 남고, 실제 `db-secrets.env`/`app-secrets.env`는 로컬에서 생성합니다.
  - `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/db-secrets.env`
  - `/Users/junsu/Desktop/2-junsu-community-be/k8s/base/config/app-secrets.env`
- 배포 스크립트:
  - `./scripts/k8s_up_local.sh`
  - `./scripts/k8s_down_local.sh`
  - `./scripts/k8s_qa_local.sh`
  - `./scripts/k8s_dm_multi_pod_proof.sh`
- 배포 모드:
  - 기본: `K8S_TARGET=base ./scripts/k8s_up_local.sh`
  - DM 분산 증빙: `K8S_TARGET=dm-scale-proof ./scripts/k8s_up_local.sh`
- 기본 접속:
  - `./scripts/k8s_up_local.sh`가 `svc/community-nginx -> 127.0.0.1:30080` port-forward를 자동 시작
  - 앱: `http://127.0.0.1:30080`
  - Swagger: `http://127.0.0.1:30080/docs`
- DM 분산 증빙:
  - `K8S_TARGET=dm-scale-proof`에서 `community-be` Pod 2개로 확장한 뒤
  - `./scripts/k8s_dm_multi_pod_proof.sh`가 서로 다른 Pod IP에 직접 붙어 Redis pub/sub 기반 실시간 전달을 검증합니다.
- 상세 가이드:
  - `/Users/junsu/Desktop/2-junsu-community-be/docs/K8S_LOCAL_GUIDE.md`

---

## 🛡 Terraform 운영 기본값

- `infra/terraform/variables.tf` 기준 기본값
  - `minimal_cost_mode=true`
  - `assign_eip=false`
  - `enable_rds=false` (최소비용 기본 운영)
  - `enable_ecs=false`
  - `enable_nat_gateway=false`
  - `enable_alb=false`
  - `enable_efs=false`
  - `enable_cloudtrail=false`
- `infra/terraform/terraform.tfvars.example`의 `admin_cidr`는 샘플 `/32`로 제공됩니다.
  - `admin_cidr=0.0.0.0/0`는 `terraform validate`에서 차단됩니다.
- remote backend 예시:
  - `infra/terraform/backend.tf.example`
  - `infra/terraform/backend.hcl.example`
  - `backend.tf`와 `backend.hcl`을 복사하면 `scripts/infra_*.sh`가 `backend.hcl`을 자동 감지합니다.
  - `backend.tf`만 있고 `backend.hcl`이 없으면 스크립트는 즉시 실패합니다.
  - 예외적으로 로컬 state가 필요할 때만 `TF_FORCE_LOCAL_BACKEND=true`를 명시합니다.
- 업로드 보안:
  - Presigned URL 발급은 인증된 BE 경유 `POST /v1/files/upload-url`만 허용
  - 업로드 Lambda는 `X-Upload-Internal-Token` 헤더가 없는 직접 호출을 차단
  - `upload_allowed_origin`은 단일 Origin만 허용하며 `"*"`는 `terraform validate`에서 차단
- 배포 env 보안:
  - `scripts/ensure_deploy_proxy_env.sh`는 `MODE=deploy`에서 DB 비밀번호를 fail-fast로 검증합니다.
  - `MYSQL_ROOT_PASSWORD`, `DB_PASSWORD`가 빈값/placeholder(`change_me_*`, `community_*`)면 배포를 중단합니다.

## 📦 의존성 기준

- 런타임 배포 기준 의존성 파일은 `requirements.txt`입니다.
- `pyproject.toml`은 메타데이터/개발 편의용이며, 다음 명령으로 정합성을 수시 점검합니다.

```bash
python3 - <<'PY'
from pathlib import Path
req = {line.split("==")[0].split(">=")[0].strip() for line in Path("requirements.txt").read_text().splitlines() if line.strip() and not line.startswith("#")}
print("requirements entries:", sorted(req))
PY
```

---

## ✨ 주요 기능

### 👤 회원 관리
| 기능 | 설명 |
|:---|:---|
| 회원가입 | 이메일/비밀번호/닉네임/프로필 이미지 등록 |
| 로그인 | 이메일/비밀번호 인증, 세션 기반 |
| 로그아웃 | 세션 종료 및 로컬 데이터 정리 |
| 회원 탈퇴 | 계정 및 관련 데이터 영구 삭제 |

### 📝 게시글 관리
| 기능 | 설명 |
|:---|:---|
| 게시글 작성 | 제목, 내용, 이미지 첨부 |
| 게시글 조회 | 무한 스크롤, 조회수 표시 |
| 게시글 수정 | 본인 게시글만 수정 가능 |
| 게시글 삭제 | 본인 게시글만 삭제 가능 |
| 좋아요 | 좋아요/좋아요 취소 토글 |

### 💬 댓글 관리
| 기능 | 설명 |
|:---|:---|
| 댓글 작성 | 게시글에 댓글 작성 |
| 댓글 수정 | 본인 댓글만 수정 가능 |
| 댓글 삭제 | 본인 댓글만 삭제 가능 |

### 📩 실시간 DM
| 기능 | 설명 |
|:---|:---|
| 1:1 실시간 채팅 | FastAPI WebSocket 기반 DM |
| 분산 전달 | Redis pub/sub으로 서로 다른 BE Pod 간 fan-out |
| 읽음/미읽음 | `dm_room_reads` 기반 읽음 표시 및 미읽음 집계 |
| 부재 알림 | 상대가 해당 DM 방 WebSocket에 연결되어 있지 않으면 Browser Web Push 발송 |

### ⚙️ 프로필 관리
| 기능 | 설명 |
|:---|:---|
| 프로필 이미지 변경 | 새 이미지 업로드 |
| 닉네임 변경 | 1~10자, 특수문자/공백 불가 |
| 비밀번호 변경 | 기존 비밀번호 확인 후 변경 |

<br>

---

## 🛠 기술 스택

| 구분 | 기술 |
|:---:|:---|
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black) |
| **Server** | ![Node.js](https://img.shields.io/badge/Node.js-339933?style=flat&logo=node.js&logoColor=white) ![Express](https://img.shields.io/badge/Express-000000?style=flat&logo=express&logoColor=white) |
| **Backend API** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) (별도 서버) |

<br>

---

## 📁 프로젝트 구조

```
📦 2-junsu-community-fe
├── 📂 public
│   ├── 📂 css                    # 스타일시트
│   │   ├── common.css            # 공통 스타일
│   │   ├── login.css             # 로그인 페이지
│   │   ├── signup.css            # 회원가입 페이지
│   │   ├── posts.css             # 게시글 목록
│   │   ├── post_detail.css       # 게시글 상세
│   │   ├── post_write.css        # 게시글 작성/수정
│   │   ├── profile.css           # 프로필 관리
│   │   └── password.css          # 비밀번호 변경
│   │
│   ├── 📂 js                     # JavaScript 파일
│   │   ├── common.js             # 공통 유틸리티 (API URL, 포맷터 등)
│   │   ├── modal.js              # 커스텀 모달 컴포넌트
│   │   ├── login.js              # 로그인 로직
│   │   ├── signup.js             # 회원가입 로직
│   │   ├── posts.js              # 게시글 목록 (무한 스크롤)
│   │   ├── post_detail.js        # 게시글 상세 (좋아요, 댓글)
│   │   ├── post_write.js         # 게시글 작성
│   │   ├── post_edit.js          # 게시글 수정
│   │   ├── profile.js            # 프로필 관리
│   │   └── password.js           # 비밀번호 변경
│   │
│   ├── 📄 index.html             # 게시글 목록 페이지
│   ├── 📄 login.html             # 로그인 페이지
│   ├── 📄 signup.html            # 회원가입 페이지
│   ├── 📄 post_detail.html       # 게시글 상세 페이지
│   ├── 📄 post_write.html        # 게시글 작성 페이지
│   ├── 📄 post_edit.html         # 게시글 수정 페이지
│   ├── 📄 profile.html           # 프로필 관리 페이지
│   └── 📄 password.html          # 비밀번호 변경 페이지
│
├── 📂 src
│   └── 📄 server.js              # Express 정적 파일 서버
│
├── 📄 package.json
└── 📄 README.md
```

<br>

---

## ⚙️ 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/hahark-ops/2-junsu-community-fe.git
cd 2-junsu-community-fe
```

### 2. 의존성 설치
```bash
npm install
```

### 3. 서버 실행
```bash
npm start
```

### 4. 브라우저 접속
```
http://localhost:3000
```

> ⚠️ **주의**: 백엔드 API 서버(`localhost:8000`)가 실행 중이어야 정상 동작합니다.

<br>

---

## 📑 페이지 상세

### � 로그인 (`login.html`)

**경로**: `/` (루트) 또는 `/login.html`

| 기능 | 설명 |
|:---|:---|
| 이메일 입력 | 형식 검증 (예: `example@example.com`) |
| 비밀번호 입력 | 8~20자, 대/소문자/숫자/특수문자 포함 |
| 로그인 버튼 | 모든 입력이 유효할 때만 활성화 |
| 회원가입 링크 | `/signup.html`로 이동 |

**유효성 검사**:
- 이메일: 정규식 패턴 `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
- 비밀번호: 정규식 패턴 `/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$/`

---

### 📝 회원가입 (`signup.html`)

**경로**: `/signup.html`

| 기능 | 설명 |
|:---|:---|
| 프로필 이미지 | 클릭하여 이미지 선택, 미리보기 표시 |
| 이메일 | 형식 검증 + **실시간 중복 확인** |
| 비밀번호 | 8~20자, 대/소문자/숫자/특수문자 필수 |
| 비밀번호 확인 | 비밀번호 일치 여부 확인 |
| 닉네임 | 1~10자, 특수문자/공백 불가 + **실시간 중복 확인** |

**API 호출**:
- `GET /v1/auth/emails/availability?email=...` - 이메일 중복 확인
- `GET /v1/auth/nicknames/availability?nickname=...` - 닉네임 중복 확인
- `POST /v1/files` - 프로필 이미지 업로드
- `POST /v1/auth/signup` - 회원가입 처리

---

### 📋 게시글 목록 (`index.html`)

**경로**: `/posts`

| 기능 | 설명 |
|:---|:---|
| 게시글 카드 | 제목, 좋아요/댓글/조회수, 작성일, 작성자 표시 |
| 무한 스크롤 | IntersectionObserver 활용, 10개씩 로드 |
| 게시글 클릭 | 해당 게시글 상세 페이지로 이동 |
| 글쓰기 버튼 | `/post_write.html`로 이동 |
| 프로필 드롭다운 | 프로필 관리, 비밀번호 변경, 로그아웃 |

**bfcache 대응**:
- `pageshow` 이벤트로 뒤로가기 시 데이터 새로고침

---

### 📄 게시글 상세 (`post_detail.html`)

**경로**: `/post_detail.html?id={postId}`

| 기능 | 설명 |
|:---|:---|
| 게시글 표시 | 제목, 작성자, 작성일, 내용, 이미지 |
| 좋아요 버튼 | 토글 방식 (좋아요/취소) |
| 조회수 | 페이지 접근 시 자동 증가 |
| 수정/삭제 버튼 | 본인 게시글인 경우에만 표시 |
| 댓글 목록 | 작성, 수정, 삭제 (본인만) |

**삭제 확인**:
- 커스텀 모달로 삭제 전 확인

---

### ✏️ 게시글 작성 (`post_write.html`)

**경로**: `/post_write.html`

| 기능 | 설명 |
|:---|:---|
| 제목 입력 | 최대 26자 |
| 내용 입력 | 텍스트 영역 |
| 이미지 첨부 | 파일 선택, 미리보기 |
| 작성 버튼 | 제목과 내용 입력 시 활성화 |

---

### 🔄 게시글 수정 (`post_edit.html`)

**경로**: `/post_edit.html?id={postId}`

| 기능 | 설명 |
|:---|:---|
| 기존 데이터 로드 | 제목, 내용, 이미지 불러오기 |
| 이미지 변경 | 새 이미지 업로드 또는 기존 유지 |
| 수정 완료 | 변경된 내용 저장 |

---

### 👤 프로필 관리 (`profile.html`)

**경로**: `/profile.html`

| 기능 | 설명 |
|:---|:---|
| 이메일 표시 | 변경 불가 (읽기 전용) |
| 프로필 이미지 변경 | 클릭하여 새 이미지 선택 |
| 닉네임 변경 | 1~10자, 특수문자/공백 불가 |
| 회원 탈퇴 | 모달 확인 후 계정 및 관련 데이터 영구 삭제 |

**토스트 알림**:
- 프로필 수정 완료 시 하단 토스트 표시

---

### 🔒 비밀번호 변경 (`password.html`)

**경로**: `/password.html`

| 기능 | 설명 |
|:---|:---|
| 현재 비밀번호 | 기존 비밀번호 입력 |
| 새 비밀번호 | 8~20자, 대/소문자/숫자/특수문자 필수 |
| 새 비밀번호 확인 | 새 비밀번호 일치 확인 |

**유효성 검사**:
- 새 비밀번호가 현재 비밀번호와 동일하면 에러
- 모든 조건 만족 시 수정 버튼 활성화

<br>

---

## 🧩 공통 컴포넌트

### `common.js`
```javascript
const API_BASE_URL = 'http://localhost:8000';  // 백엔드 API 주소

function formatNumber(num) { ... }  // 숫자 포맷팅 (1000 → 1k)
function formatDate(dateString) { ... }  // 날짜 포맷팅
function showCustomModal(message, callback) { ... }  // 알림 모달
```

### `modal.js`
- 재사용 가능한 커스텀 확인/취소 모달 컴포넌트

<br>

---

## 🔗 관련 저장소

| 저장소 | 설명 |
|:---|:---|
| [2-junsu-community-be](https://github.com/hahark-ops/2-junsu-community-be) | FastAPI 백엔드 서버 |

<br>

---

<p align="center">
  Made with ❤️ by junsu
</p>
