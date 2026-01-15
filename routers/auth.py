from fastapi import APIRouter, Response, Request, status
from controllers.auth import auth_signup, auth_login, auth_logout
from models.auth import SignupRequest, LoginRequest

router = APIRouter(prefix="/v1/auth")

@router.post("/signup", status_code=201)
async def signup(user_data: SignupRequest):
    return await auth_signup(user_data)

@router.post("/login", status_code=200)
async def login(response: Response, login_data: LoginRequest):
    return await auth_login(response, login_data)

@router.post("/logout", status_code=200)
async def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    return await auth_logout(response, session_id)