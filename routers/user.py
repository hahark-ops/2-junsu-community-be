from fastapi import APIRouter, status, Depends, Body
from controllers.user import get_my_info, get_user_by_id
from controllers.auth import auth_signup
from dependencies import get_current_user

router = APIRouter(prefix="/v1/users")

@router.post("", status_code=status.HTTP_201_CREATED)
async def signup(user_data: dict = Body(...)):
    return await auth_signup(user_data)

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(user: dict = Depends(get_current_user)):
    return await get_my_info(user)

@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(user_id: int):
    return await get_user_by_id(user_id)