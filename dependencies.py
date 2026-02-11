from fastapi import Request
from database import fake_sessions, fake_users
from utils import APIException

# 로그인한 사용자 찾기 (없으면 에러 401)
async def get_current_user(request: Request):
    # 1. 쿠키에서 세션 ID 가져오기
    session_id = request.cookies.get("session_id")
    
    # 2. 세션이 없거나, 유효하지 않으면 튕겨냄
    if not session_id or session_id not in fake_sessions:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="로그인이 필요한 기능입니다.",
            status_code=401
        )
    
    # 3. 세션 ID로 유저 이메일 찾기
    user_email = fake_sessions[session_id]
    
    # 4. 유저 정보 반환
    for user in fake_users:
        if user["email"] == user_email:
            return user
            
    # 유저가 삭제됐을 경우
    raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=401)