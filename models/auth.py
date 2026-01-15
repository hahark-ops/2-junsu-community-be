from pydantic import BaseModel
from typing import Optional

class SignupRequest(BaseModel):
    email: str
    password: str
    nickname: str
    profileimage: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None