from fastapi import Response
import uuid  # 세션 ID 생성용
from database import get_db_connection
from utils import validate_email, validate_password, validate_nickname, validate_nickname_length, APIException
from datetime import datetime, timedelta

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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 3. 이메일 중복 체크
        query = "SELECT id FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        if cursor.fetchone():
            raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 사용 중인 이메일입니다.", status_code=409)
        
        return {
            "code": "EMAIL_AVAILABLE",
            "message": "사용 가능한 이메일입니다.",
            "data": None
        }
    finally:
        cursor.close()
        conn.close()

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
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 4. 닉네임 중복 체크
        query = "SELECT id FROM users WHERE nickname = %s"
        cursor.execute(query, (nickname,))
        if cursor.fetchone():
            raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)
        
        return {
            "code": "NICKNAME_AVAILABLE",
            "message": "사용 가능한 닉네임입니다.",
            "data": None
        }
    finally:
        cursor.close()
        conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 5. 이메일 중복 체크 (탈퇴한 사용자는 제외? 보통은 이메일 유니크라 탈퇴해도 못쓰게 하거나, 탈퇴시 이메일 변경 등의 정책 필요)
        # 여기서는 is_deleted = True면 재가입 허용? 
        # API 명세상 "이미 가입된 이메일" 체크.
        # DB UNIQUE 제약조건이 있으므로 중복 INSERT 시 에러 발생함.
        # 하지만 명확한 에러 메시지를 위해 조회 먼저.
        
        check_query = "SELECT id, is_deleted FROM users WHERE email = %s"
        cursor.execute(check_query, (user_data["email"],))
        existing_user = cursor.fetchone()
        
        if existing_user:
            if not existing_user["is_deleted"]:
                raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다.", status_code=409)
            else:
                # 탈퇴한 회원이면? 재가입 정책에 따라 다름. 여기서는 일단 중복 에러로 막거나, 복구 로직이 필요.
                # 간단하게 "이미 가입된"으로 처리
                raise APIException(code="ALREADY_EXIST_EMAIL", message="이미 가입된 이메일입니다. (탈퇴 계정)", status_code=409)

        # 닉네임 중복 체크
        check_nick_query = "SELECT id FROM users WHERE nickname = %s"
        cursor.execute(check_nick_query, (user_data["nickname"],))
        if cursor.fetchone():
             raise APIException(code="ALREADY_EXIST_NICKNAME", message="이미 사용 중인 닉네임입니다.", status_code=409)

        # 6. 저장
        # PASSWORD HASHING should be here in real app, but using plaintext as per "basics" request
        insert_query = "INSERT INTO users (email, password, nickname) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (user_data["email"], user_data["password"], user_data["nickname"]))
        user_id = cursor.lastrowid
        
        # 프로필 이미지 저장 (있다면)
        if user_data.get("profileimage"):
             # TODO: file_name, file_size 처리는? 
             # 여기서는 URL만 들어오므로 임시 값 넣거나 프로필 이미지 로직 보완 필요.
             # 일단 스키마에 맞춰서 넣음.
             file_query = """
                INSERT INTO files (file_type, user_id, file_url, file_name, file_size) 
                VALUES ('profile', %s, %s, 'profile.jpg', 0)
             """
             cursor.execute(file_query, (user_id, user_data["profileimage"]))

        conn.commit()
        
        return {
            "code": "SIGNUP_SUCCESS", 
            "message": "회원가입이 완료되었습니다.", 
            "data": None
        }
    except Exception as e:
        conn.rollback()
        # 이미 APIException은 상위로 전파, 그 외 DB 에러 처리
        if isinstance(e, APIException):
            raise e
        print(f"Signup Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="회원가입 중 오류가 발생했습니다.", status_code=500)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 2. 로그인
# ==========================================
async def auth_login(response: Response, login_data: dict):
    # 필수값 체크
    if not login_data.get("email") or not login_data.get("password"):
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="이메일과 비밀번호는 필수입니다.", status_code=400)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 사용자 조회
        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (login_data["email"], login_data["password"]))
        user = cursor.fetchone()
        
        if not user:
            raise APIException(code="LOGIN_FAILED", message="이메일 또는 비밀번호가 일치하지 않습니다.", status_code=400) # 보안상 401 권장

        # 탈퇴한 회원 로그인 금지
        if user["is_deleted"]:
            raise APIException(code="ACCOUNT_DELETED", message="탈퇴한 계정입니다. 다시 가입해주세요.", status_code=403)

        # 세션 생성 및 쿠키 굽기
        session_id = str(uuid.uuid4())
        
        # 세션 만료 시간 (예: 24시간)
        expires_at = datetime.now() + timedelta(hours=24)
        
        session_query = "INSERT INTO sessions (user_id, session_id, expires_at) VALUES (%s, %s, %s)"
        cursor.execute(session_query, (user["id"], session_id, expires_at))
        conn.commit()
        
        response.set_cookie(key="session_id", value=session_id, httponly=True)

        return {
            "code": "LOGIN_SUCCESS", 
            "message": "로그인 성공", 
            "data": {"email": user["email"]}
        }
    except Exception as e:
        conn.rollback()
        if isinstance(e, APIException):
            raise e
        print(f"Login Error: {e}")
        raise APIException(code="INTERNAL_ERROR", message="로그인 처리 중 오류 발생", status_code=500)
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
            query = "DELETE FROM sessions WHERE session_id = %s"
            cursor.execute(query, (session_id,))
            conn.commit()
        except Exception:
            pass # 로그아웃은 조용히 실패해도 넘어감
        finally:
            cursor.close()
            conn.close()
    
    response.delete_cookie("session_id")
    return {
        "code": "LOGOUT_SUCCESS", 
        "message": "로그아웃 성공", 
        "data": None
    }