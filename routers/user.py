from fastapi import APIRouter, status, Depends, Body
from controllers.user import get_user_by_id, update_user, change_password, delete_user
from dependencies import get_current_user

router = APIRouter(prefix="/v1/users")

@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(user_id: int):
    return await get_user_by_id(user_id)

@router.patch("/{user_id}", status_code=status.HTTP_200_OK)
async def update_user_endpoint(
    user_id: int, 
    update_data: dict = Body(...), 
    user: dict = Depends(get_current_user)
):
    return await update_user(user_id, update_data, user)

@router.patch("/{user_id}/password", status_code=status.HTTP_200_OK)
async def change_password_endpoint(
    user_id: int, 
    password_data: dict = Body(...), 
    user: dict = Depends(get_current_user)
):
    return await change_password(user_id, password_data, user)

@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_user_endpoint(user: dict = Depends(get_current_user)):
    return await delete_user(user)