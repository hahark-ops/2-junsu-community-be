from fastapi import APIRouter, status
from controllers.user import get_user_info

router = APIRouter(prefix="/v1/users")

@router.get("/info/{email}", status_code=status.HTTP_200_OK)
async def get_user(email: str):
    return await get_user_info(email)