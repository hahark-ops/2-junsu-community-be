from fastapi import Request
from database import get_db_connection
from utils import APIException

# 로그인한 사용자 찾기 (없으면 에러 401)
async def get_current_user(request: Request):
    # 1. 쿠키에서 세션 ID 가져오기
    session_id = request.cookies.get("session_id")
    
    # 2. 세션 ID 없으면 튕겨냄
    if not session_id:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="로그인이 필요한 기능입니다.",
            status_code=401
        )
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 3. DB에서 세션 확인
        cursor.execute("SELECT userEmail FROM sessions WHERE sessionId = %s", (session_id,))
        session = cursor.fetchone()
        
        if not session:
             raise APIException(
                code="LOGIN_REQUIRED",
                message="유효하지 않은 세션입니다. 다시 로그인해주세요.",
                status_code=401
            )
            
        user_email = session["userEmail"]
        
        # 4. 유저 정보 조회
        cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()
        
        if not user:
            raise APIException(code="USER_NOT_FOUND", message="사용자를 찾을 수 없습니다.", status_code=401)
            
        return user
        
    finally:
        cursor.close()
        conn.close()
