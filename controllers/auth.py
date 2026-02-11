import os
import uuid

from fastapi import Response

from models import auth_model, user_model
from utils import (
    APIException,
    hash_password,
    is_hashed_password,
    validate_email,
    validate_nickname,
    validate_nickname_length,
    validate_password,
    verify_password,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _cookie_samesite() -> str:
    value = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
COOKIE_SAMESITE = _cookie_samesite()
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None

try:
    COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE", "604800"))
except ValueError:
    COOKIE_MAX_AGE = 604800

# ==========================================
# 0. 이메일 중복 체크
# ==========================================
async def check_email_availability(email: str | None):
    if not email:
        raise APIException(code="EMAIL_PARAM_MISSING", message="검사할 이메일 주소를 입력해주세요.", status_code=400)
    
    if not validate_email(email):
        raise APIException(code="INVALID_EMAIL_FORMAT", message="올바른 이메일 형식이 아닙니다.", status_code=400)
    
    if auth_model.count_users_by_email(email) > 0:
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
    if not nickname:
        raise APIException(code="NICKNAME_PARAM_MISSING", message="닉네임을 입력해주세요.", status_code=400)
    
    if not validate_nickname_length(nickname):
        raise APIException(code="NICKNAME_TOO_LONG", message="닉네임은 최대 10자까지만 가능합니다.", status_code=400)
    
    if not validate_nickname(nickname):
        raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)
    
    if auth_model.count_users_by_nickname(nickname) > 0:
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
    if not all([user_data.get("email"), user_data.get("password"), user_data.get("nickname")]):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="이메일, 비밀번호, 닉네임은 필수 입력 사항입니다.", status_code=400)

    if not validate_email(user_data["email"]):
        raise APIException(code="INVALID_EMAIL_FORMAT", message="유효하지 않은 이메일 형식입니다.", status_code=400)

    if not validate_password(user_data["password"]):
        raise APIException(code="WEAK_PASSWORD", message="비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.", status_code=400)

    if not validate_nickname(user_data["nickname"]):
        raise APIException(code="INVALID_NICKNAME_FORMAT", message="닉네임에 공백이나 특수문자를 포함할 수 없습니다.", status_code=400)

    # Legacy soft-deleted 계정 정리: 재가입 시 email/nickname 재사용 가능하도록 처리
    auth_model.purge_deleted_users_for_signup(user_data["email"], user_data["nickname"])

    if auth_model.count_users_by_email(user_data["email"]) > 0:
        raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다.", status_code=409)
    if auth_model.count_users_by_nickname(user_data["nickname"]) > 0:
        raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)

    profile_image = user_data.get("profileImage")
    if profile_image is None:
        profile_image = user_data.get("profileimage")

    password_hash = hash_password(user_data["password"])
    auth_model.create_user(
        email=user_data["email"],
        password_hash=password_hash,
        nickname=user_data["nickname"],
        profile_image=profile_image,
    )
    
    return {
        "code": "SIGNUP_SUCCESS", 
        "message": "회원가입이 완료되었습니다.", 
        "data": None
    }

# ==========================================
# 2. 로그인
# ==========================================
async def auth_login(response: Response, login_data: dict):
    if not login_data.get("email") or not login_data.get("password"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="이메일과 비밀번호는 필수입니다.", status_code=400)
    
    user = auth_model.get_user_by_email(login_data["email"])
    if not user:
        raise APIException(code="LOGIN_FAILED", message="이메일 또는 비밀번호가 일치하지 않습니다.", status_code=400)

    if not verify_password(login_data["password"], user.get("password")):
        raise APIException(code="LOGIN_FAILED", message="이메일 또는 비밀번호가 일치하지 않습니다.", status_code=400)

    if user.get("is_deleted"):
        raise APIException(code="LOGIN_FAILED", message="탈퇴한 회원입니다.", status_code=403)

    if not is_hashed_password(user.get("password")):
        user_model.update_user_password(user["userId"], hash_password(login_data["password"]))

    session_id = str(uuid.uuid4())
    auth_model.create_session(session_id=session_id, user_email=user["email"])

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
        domain=COOKIE_DOMAIN,
        path="/",
    )

    return {
        "code": "LOGIN_SUCCESS",
        "message": "로그인 성공",
        "data": {
            "userId": user["userId"],
            "email": user["email"],
            "nickname": user["nickname"],
            "profileImage": user.get("profileimage"),
        },
    }

# ==========================================
# 3. 로그아웃
# ==========================================
async def auth_logout(response: Response, session_id: str):
    if session_id:
        try:
            auth_model.delete_session(session_id)
        except Exception as e:
            print(f"Logout error: {e}")
    
    response.delete_cookie(
        key="session_id",
        domain=COOKIE_DOMAIN,
        path="/",
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
    return {
        "code": "LOGOUT_SUCCESS", 
        "message": "로그아웃 성공", 
        "data": None
    }
