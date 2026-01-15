# database.py

# 1. 회원 데이터
fake_users = [
    # 테스트용 계정 (서버 껐다 켜도 사용 가능)
    {
        "userId": 1,
        "email": "test@test.com",
        "password": "Password123!",
        "nickname": "테스트유저",
        "profileimage": None
    }
]

# 2. 게시글 데이터
fake_posts = []

# 3. 댓글 데이터
fake_comments = []

# 4. 세션 저장소 (로그인 상태 유지용)
# 형식: { "session_id_문자열": "user_email" }
fake_sessions = {}