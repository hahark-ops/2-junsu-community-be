from fastapi import APIRouter, Body, Depends, status

from controllers.webpush import get_webpush_status, subscribe_webpush, unsubscribe_webpush
from dependencies import get_current_user

router = APIRouter(prefix="/v1/notifications/webpush")


@router.get("/status", status_code=status.HTTP_200_OK)
async def webpush_status_endpoint(user: dict = Depends(get_current_user)):
    return await get_webpush_status(user)


@router.post("/subscribe", status_code=status.HTTP_200_OK)
async def subscribe_webpush_endpoint(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    return await subscribe_webpush(user, payload)


@router.delete("/subscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_webpush_endpoint(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    return await unsubscribe_webpush(user, payload)
