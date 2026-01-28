# models/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# ==========================================
# 요청 모델 (Request)
# ==========================================

class UserCreate(BaseModel):
    """회원가입 요청"""
    email: str
    password: str
    nickname: str
    profileImage: Optional[str] = None

class UserLogin(BaseModel):
    """로그인 요청"""
    email: str
    password: str

class UserUpdate(BaseModel):
    """회원정보 수정 요청"""
    nickname: Optional[str] = None
    profileImage: Optional[str] = None

class PasswordChange(BaseModel):
    """비밀번호 변경 요청"""
    currentPassword: str
    newPassword: str

# ==========================================
# 응답 모델 (Response)
# ==========================================

class UserResponse(BaseModel):
    """사용자 정보 응답"""
    userId: int
    email: str
    nickname: str
    profileImage: Optional[str] = None
