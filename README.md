# 🌐 아무 말 대잔치 - 커뮤니티 게시판

> 자유롭게 소통하는 커뮤니티 게시판 서비스입니다.

<br>

## 📖 목차

- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
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

## ✨ 주요 기능

### 👤 회원 관리
| 기능 | 설명 |
|:---|:---|
| 회원가입 | 이메일/비밀번호/닉네임/프로필 이미지 등록 |
| 로그인 | 이메일/비밀번호 인증, 세션 기반 |
| 로그아웃 | 세션 종료 및 로컬 데이터 정리 |
| 회원 탈퇴 | 계정 영구 삭제 |

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
| 회원 탈퇴 | 모달 확인 후 계정 삭제 |

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
