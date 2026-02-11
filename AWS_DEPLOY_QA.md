# AWS EC2 분리 배포 + QA 가이드

## 1. 아키텍처
- FE EC2: `2-junsu-community-fe` (Express + static + reverse proxy)
- BE EC2: `2-junsu-community-be` (FastAPI + MySQL)

## 2. 백엔드(EC2-BE) 설정
1. `.env.example`를 복사해 `.env` 생성
2. 필수 값 설정
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `CORS_ALLOW_ORIGINS` (FE 주소 포함)
- `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN` (도메인/HTTPS 정책에 맞게)
3. 의존성 설치
```bash
pip install -r requirements.txt
```
4. 실행
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 3. 프론트(EC2-FE) 설정
1. `.env.example`를 복사해 `.env` 생성
2. `BACKEND_TARGET`에 BE 주소 설정 (예: `http://<BE_PUBLIC_IP>:8000`)
3. 실행
```bash
npm install
npm start
```

## 4. API QA 체크리스트
- `GET /` (BE 헬스체크)
- 회원가입
  - `GET /v1/auth/emails/availability`
  - `GET /v1/auth/nicknames/availability`
  - `POST /v1/auth/signup`
- 로그인/로그아웃
  - `POST /v1/auth/login`
  - `GET /v1/auth/me`
  - `POST /v1/auth/logout`
- 게시글
  - `GET /v1/posts`
  - `POST /v1/posts`
  - `GET /v1/posts/{post_id}`
  - `PATCH /v1/posts/{post_id}`
  - `DELETE /v1/posts/{post_id}`
  - `POST /v1/posts/{post_id}/likes`
  - `DELETE /v1/posts/{post_id}/likes`
- 댓글
  - `GET /v1/posts/{post_id}/comments`
  - `POST /v1/posts/{post_id}/comments`
  - `PATCH /v1/posts/{post_id}/comments/{comment_id}`
  - `DELETE /v1/posts/{post_id}/comments/{comment_id}`
- 사용자
  - `PATCH /v1/users/{user_id}`
  - `PATCH /v1/users/{user_id}/password`
  - `DELETE /v1/users/me`
- 파일
  - `POST /v1/files/upload` (형식/용량 제한 확인)

## 5. UI QA 체크리스트
- 로그인/회원가입/로그아웃
- 게시글 작성/수정/삭제/상세/좋아요
- 댓글 작성/수정/삭제
- 프로필 수정(닉네임 + 이미지)
- 비밀번호 변경
- 회원 탈퇴
- 이미지 업로드 후 `/uploads/...` 접근 가능 여부

