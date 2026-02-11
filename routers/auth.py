from fastapi import APIRouter, Response, Request, Body, Depends, status, Query
from controllers.auth import auth_signup, auth_login, auth_logout, check_email_availability, check_nickname_availability
from controllers.user import get_my_info
from dependencies import get_current_user

router = APIRouter(prefix="/v1/auth")

@router.get("/emails/availability", status_code=status.HTTP_200_OK)
async def check_email(email: str | None = Query(default=None)):
    return await check_email_availability(email)

@router.get("/nicknames/availability", status_code=status.HTTP_200_OK)
async def check_nickname(nickname: str | None = Query(default=None)):
    return await check_nickname_availability(nickname)

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: dict = Body(...)):
    return await auth_signup(user_data)

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(response: Response, login_data: dict = Body(...)):
    return await auth_login(response, login_data)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    return await auth_logout(response, session_id)

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(user: dict = Depends(get_current_user)):
    return await get_my_info(user)
