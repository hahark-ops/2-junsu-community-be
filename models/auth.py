from pydantic import BaseModel, field_validator
from typing import Optional
from utils import validate_email, validate_password, validate_nickname

class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str
    profileimage: Optional[str] = None

    @field_validator('email')
    @classmethod
    def check_email(cls, v: str) -> str:
        if not validate_email(v):
            raise ValueError('유효하지 않은 이메일 형식입니다.')
        return v

    @field_validator('password')
    @classmethod
    def check_password(cls, v: str) -> str:
        if not validate_password(v):
            raise ValueError('비밀번호는 영문, 숫자, 특수문자를 포함하여 8~20자여야 합니다.')
        return v

    @field_validator('nickname')
    @classmethod
    def check_nickname(cls, v: str) -> str:
        if not validate_nickname(v):
            raise ValueError('닉네임에 공백이나 특수문자를 포함할 수 없습니다.')
        return v

class LoginRequest(BaseModel):
    email: str
    password: str

class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None