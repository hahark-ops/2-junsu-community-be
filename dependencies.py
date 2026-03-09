from fastapi import Request
from models import auth_model, user_model
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
    
    user_email = auth_model.get_user_email_by_session_id(session_id)
    if not user_email:
        raise APIException(
            code="LOGIN_REQUIRED",
            message="유효하지 않은 세션입니다. 다시 로그인해주세요.",
            status_code=401
        )
        
    user = user_model.get_user_by_email(user_email)
    if not user:
        try:
            auth_model.delete_session(session_id)
        except Exception:
            pass
        raise APIException(
            code="LOGIN_REQUIRED",
            message="유효하지 않은 세션입니다. 다시 로그인해주세요.",
            status_code=401,
        )
        
    return user
