from fastapi import Response, status
from fastapi.responses import JSONResponse
import uuid  # 세션 ID 생성용
from database import fake_users, fake_sessions
from models.auth import SignupRequest, LoginRequest
from utils import validate_email, validate_password, validate_nickname

# ==========================================
# 1. 회원가입
# ==========================================
async def auth_signup(user_data: SignupRequest):
    
    # 1. 필수값 누락 체크 (설계도: REQUIRED_FIELDS_MISSING)
    if not user_data.email or not user_data.password or not user_data.nickname:
        return JSONResponse(status_code=400, content={
            "code": "REQUIRED_FIELDS_MISSING",
            "message": "이메일, 비밀번호, 닉네임은 필수 입력 사항입니다.",
            "data": None
        })

    # 2. 이메일 형식 검사 (설계도: INVALID_EMAIL_FORMAT)
    if not validate_email(user_data.email):
        return JSONResponse(status_code=400, content={
            "code": "INVALID_EMAIL_FORMAT",
            "message": "유효하지 않은 이메일 형식입니다. 다시 확인해주세요.",
            "data": None
        })

    # 3. 비밀번호 강도 검사 (설계도: WEAK_PASSWORD)
    if not validate_password(user_data.password):
        return JSONResponse(status_code=400, content={
            "code": "WEAK_PASSWORD",
            "message": "비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.",
            "data": None
        })

    # 4. 닉네임 형식 검사 (설계도: INVALID_NICKNAME_FORMAT)
    if not validate_nickname(user_data.nickname):
        return JSONResponse(status_code=400, content={
            "code": "INVALID_NICKNAME_FORMAT",
            "message": "닉네임에 공백이나 특수문자를 포함할 수 없습니다.",
            "data": None
        })

    # 5. 이메일 중복 체크 (설계도: ALREADY_EXIST_EMAIL)
    for user in fake_users:
        if user["email"] == user_data.email:
            return JSONResponse(status_code=409, content={
                "code": "ALREADY_EXIST_EMAIL",
                "message": "이미 가입된 이메일입니다.",
                "data": None
            })

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
        return JSONResponse(status_code=400, content={
            "code": "LOGIN_FAILED",
            "message": "이메일 또는 비밀번호가 일치하지 않습니다.",
            "data": None
        })

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