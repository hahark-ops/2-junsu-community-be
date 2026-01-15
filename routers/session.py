from fastapi import APIRouter, Response, Request, status, Body
from controllers.auth import auth_login, auth_logout

router = APIRouter(prefix="/v1/sessions")

@router.post("", status_code=200)
async def login(response: Response, login_data: dict = Body(...)):
    return await auth_login(response, login_data)

@router.delete("", status_code=200)
async def logout(response: Response, request: Request):
    session_id = request.cookies.get("session_id")
    return await auth_logout(response, session_id)