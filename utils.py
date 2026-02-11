import re
import os

import bcrypt
from fastapi import HTTPException

# 1. 이메일 형식 검사
def validate_email(email: str) -> bool:
    email_regex = r'^[a-zA-Z0-9+_\-.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))

# 2. 비밀번호 강도 검사
# 조건: 영문, 숫자, 특수문자 포함, 8~20자
def validate_password(password: str) -> bool:
    if not (8 <= len(password) <= 20):
        return False
    
    # 정규식: 영문(?=.*[A-Za-z]), 숫자(?=.*\d), 특수문자(?=.*[@$!%*#?&]) 각각 최소 1개 포함
    pw_regex = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]+$'
    return bool(re.match(pw_regex, password))

# 3. 닉네임 형식 검사
# 조건: 공백이나 특수문자 불가 (한글, 영문, 숫자만 허용)
def validate_nickname(nickname: str) -> bool:
    # ^[가-힣a-zA-Z0-9]+$ -> 한글, 영대소문자, 숫자만 있으면 통과
    nickname_regex = r'^[가-힣a-zA-Z0-9]+$'
    return bool(re.match(nickname_regex, nickname))

# 4. 닉네임 길이 검사
# 조건: 최대 10자
def validate_nickname_length(nickname: str, max_length: int = 10) -> bool:
    return len(nickname) <= max_length


def _bcrypt_rounds() -> int:
    raw = os.getenv("BCRYPT_ROUNDS", "12")
    try:
        rounds = int(raw)
    except ValueError:
        return 12
    return max(4, min(rounds, 16))


def is_hashed_password(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_bcrypt_rounds())
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, stored_password: str | None) -> bool:
    if not stored_password:
        return False

    if is_hashed_password(stored_password):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.encode("utf-8"))
        except ValueError:
            return False

    # Legacy plaintext compatibility for existing data.
    return plain_password == stored_password

class APIException(HTTPException):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.data = None
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "data": None})
