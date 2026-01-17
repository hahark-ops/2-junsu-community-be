from fastapi import APIRouter, status
from controllers.user import get_user_by_id

router = APIRouter(prefix="/v1/users")

@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(user_id: int):
    return await get_user_by_id(user_id)