from fastapi import Response
import uuid
from database import get_db_connection
from utils import validate_email, validate_password, validate_nickname, validate_nickname_length, APIException

# ==========================================
# 0. 이메일 중복 체크
# ==========================================
async def check_email_availability(email: str | None):
    if not email:
        raise APIException(code="EMAIL_PARAM_MISSING", message="검사할 이메일 주소를 입력해주세요.", status_code=400)
    
    if not validate_email(email):
        raise APIException(code="INVALID_EMAIL_FORMAT", message="올바른 이메일 형식이 아닙니다.", status_code=400)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT count(*) as count FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        if result["count"] > 0:
            raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 사용 중인 이메일입니다.", status_code=409)
    finally:
        cursor.close()
        conn.close()
    
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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT count(*) as count FROM users WHERE nickname = %s", (nickname,))
        result = cursor.fetchone()
        if result["count"] > 0:
            raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
    finally:
        cursor.close()
        conn.close()
    
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 이메일 중복 체크
        cursor.execute("SELECT count(*) as count FROM users WHERE email = %s", (user_data["email"],))
        if cursor.fetchone()["count"] > 0:
            raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다.", status_code=409)
        
        # 닉네임 중복 체크
        cursor.execute("SELECT count(*) as count FROM users WHERE nickname = %s", (user_data["nickname"],))
        if cursor.fetchone()["count"] > 0:
            raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)

        # 저장
        sql = "INSERT INTO users (email, password, nickname, profileimage) VALUES (%s, %s, %s, %s)"
        val = (user_data["email"], user_data["password"], user_data["nickname"], user_data.get("profileimage"))
        cursor.execute(sql, val)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
    
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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (login_data["email"], login_data["password"]))
        user = cursor.fetchone()
        
        if not user:
            raise APIException(code="LOGIN_FAILED", message="이메일 또는 비밀번호가 일치하지 않습니다.", status_code=400)
            
        if user["is_deleted"]:
             raise APIException(code="LOGIN_FAILED", message="탈퇴한 회원입니다.", status_code=403)

        # 세션 생성 (DB에 저장)
        session_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO sessions (sessionId, userEmail) VALUES (%s, %s)", (session_id, user["email"]))
        conn.commit()
        
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        
        return {
            "code": "LOGIN_SUCCESS", 
            "message": "로그인 성공", 
            "data": {"email": user["email"]}
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. 로그아웃
# ==========================================
async def auth_logout(response: Response, session_id: str):
    if session_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM sessions WHERE sessionId = %s", (session_id,))
            conn.commit()
        except Exception as e:
            print(f"Logout error: {e}")
            # 로그아웃 실패해도 쿠키는 삭제
        finally:
            cursor.close()
            conn.close()
    
    response.delete_cookie("session_id")
    return {
        "code": "LOGOUT_SUCCESS", 
        "message": "로그아웃 성공", 
        "data": None
    }
