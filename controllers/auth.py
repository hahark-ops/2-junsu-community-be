from fastapi import Response
import uuid  # 세션 ID 생성용
from database import fake_users, fake_sessions
from utils import validate_email, validate_password, validate_nickname, validate_nickname_length, APIException

# ==========================================
# 0. 이메일 중복 체크
# ==========================================
async def check_email_availability(email: str | None):
    # 1. 이메일 파라미터 누락
    if not email:
        raise APIException(code="EMAIL_PARAM_MISSING", message="검사할 이메일 주소를 입력해주세요.", status_code=400)
    
    # 2. 이메일 형식 검사
    if not validate_email(email):
        raise APIException(code="INVALID_EMAIL_FORMAT", message="올바른 이메일 형식이 아닙니다.", status_code=400)
    
    # 3. 이메일 중복 체크
    for user in fake_users:
        if user["email"] == email:
            raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 사용 중인 이메일입니다.", status_code=409)
    
    return {
        "code": "EMAIL_AVAILABLE",
        "message": "사용 가능한 이메일입니다.",
        "data": None
    }

# ==========================================
# 0-1. 닉네임 중복 체크
# ==========================================
async def check_nickname_availability(nickname: str | None):
    # 1. 닉네임 파라미터 누락
    if not nickname:
        raise APIException(code="NICKNAME_PARAM_MISSING", message="닉네임을 입력해주세요.", status_code=400)
    
    # 2. 닉네임 길이 검사 (최대 10자)
    if not validate_nickname_length(nickname):
        raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
    
    # 3. 닉네임 형식 검사
    if not validate_nickname(nickname):
        raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
    
    # 4. 닉네임 중복 체크
    for user in fake_users:
        if user["nickname"] == nickname:
            raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
    
    return {
        "code": "NICKNAME_AVAILABLE",
        "message": "사용 가능한 닉네임입니다.",
        "data": None
    }

# ==========================================
# 1. 회원가입
# ==========================================
async def auth_signup(user_data: dict):
    
    # 1. 필수값 누락 체크
    if not all([user_data.get("email"), user_data.get("password"), user_data.get("nickname")]):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="이메일, 비밀번호, 닉네임은 필수 입력 사항입니다.", status_code=400)

    # 2. 이메일 형식 검사
    if not validate_email(user_data["email"]):
        raise APIException(code="INVALID_EMAIL_FORMAT", message="유효하지 않은 이메일 형식입니다.", status_code=400)

    # 3. 비밀번호 강도 검사
    if not validate_password(user_data["password"]):
        raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)

    # 4. 닉네임 형식 검사
    if not validate_nickname(user_data["nickname"]):
        raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)

    # 5. 이메일 중복 체크
    for user in fake_users:
        if user["email"] == user_data["email"]:
            raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다.", status_code=409)

    # 6. 저장
    new_id = 1
    if fake_users:
        new_id = fake_users[-1]["userId"] + 1
    
    new_user = {
        "userId": new_id,
        "email": user_data["email"],
        "password": user_data["password"],
        "nickname": user_data["nickname"],
        "profileimage": user_data.get("profileimage")
    }
    fake_users.append(new_user)
    
    return {
        "code": "SIGNUP_SUCCESS", 
        "message": "회원가입이 완료되었습니다.", 
        "data": None
    }

# ==========================================
# 2. 로그인
# ==========================================
async def auth_login(response: Response, login_data: dict):
    # 필수값 체크
    if not login_data.get("email") or not login_data.get("password"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="이메일과 비밀번호는 필수입니다.", status_code=400)
    
    user = next((u for u in fake_users if u["email"] == login_data["email"] and u["password"] == login_data["password"]), None)
    
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
    if session_id and session_id in fake_sessions:
        del fake_sessions[session_id]
    
    response.delete_cookie("session_id")
    return {
        "code": "LOGOUT_SUCCESS", 
        "message": "로그아웃 성공", 
        "data": None
    }