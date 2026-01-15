from fastapi import Response, status
import uuid  # 세션 ID 생성용
from database import fake_users, fake_sessions
from models.auth import SignupRequest, LoginRequest
from utils import APIException

# ==========================================
# 1. 회원가입
# ==========================================
async def auth_signup(user_data: SignupRequest):
    
    # note: 필수값 체크 및 데이터 형식 검증은 Pydantic Model(SignupRequest)에서 이미 처리되었습니다.

    # 1. 이메일 중복 체크 (설계도: ALREADY_EXIST_EMAIL)
    for user in fake_users:
        if user["email"] == user_data.email:
             raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다.", status_code=409)

    # 6. 저장
    new_id = 1
    if fake_users:
        new_id = fake_users[-1]["userId"] + 1
    
    new_user = user_data.model_dump()
    new_user["userId"] = new_id
    fake_users.append(new_user)
    
    return {
        "code": "SIGNUP_SUCCESS", 
        "message": "회원가입이 완료되었습니다.", 
        "data": None
    }

# ==========================================
# 2. 로그인
# ==========================================
async def auth_login(response: Response, login_data: LoginRequest):
    user = next((u for u in fake_users if u["email"] == login_data.email and u["password"] == login_data.password), None)
    
    if not user:
        raise APIException(code="LOGIN_FAILED", message="이메일 또는 비밀번호가 일치하지 않습니다.", status_code=400)

    # 세션 생성 및 쿠키 굽기
    session_id = str(uuid.uuid4())
    fake_sessions[session_id] = user["email"]
    
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    return {
        "code": "LOGIN_SUCCESS", 
        "message": "로그인 성공", 
        "data": {"email": user["email"]}
    }

# ==========================================
# 3. 로그아웃
# ==========================================
async def auth_logout(response: Response, session_id: str):
    if session_id in fake_sessions:
        del fake_sessions[session_id]
    
    response.delete_cookie("session_id")
    return {
        "code": "LOGOUT_SUCCESS", 
        "message": "로그아웃 성공", 
        "data": None
    }