from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from controllers.dm import (
    create_dm_message,
    create_or_get_room,
    dm_connection_manager,
    get_my_rooms,
    get_room_messages,
    mark_room_as_read_and_notify,
    require_room_access,
)
from dependencies import get_current_user, resolve_user_by_session_id
from models import dm_model
from utils import APIException

router = APIRouter(prefix="/v1/dm")
ws_router = APIRouter()


@router.post("/rooms", status_code=status.HTTP_200_OK)
async def create_or_get_room_endpoint(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
):
    target_user_id = payload.get("targetUserId")
    if target_user_id is None:
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="상대 사용자 정보가 필요합니다.", status_code=400)
    try:
        normalized_target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        raise APIException(code="INVALID_TARGET_USER", message="유효하지 않은 사용자입니다.", status_code=400)
    return await create_or_get_room(normalized_target_user_id, user)


@router.get("/rooms", status_code=status.HTTP_200_OK)
async def get_my_rooms_endpoint(user: dict = Depends(get_current_user)):
    return await get_my_rooms(user)


@router.get("/rooms/{room_id}/messages", status_code=status.HTTP_200_OK)
async def get_room_messages_endpoint(room_id: int, limit: int = 50, user: dict = Depends(get_current_user)):
    return await get_room_messages(room_id, user, limit=limit)


@ws_router.websocket("/ws/dm/{room_id}")
async def dm_websocket_endpoint(websocket: WebSocket, room_id: int):
    session_id = websocket.cookies.get("session_id")

    try:
        current_user = resolve_user_by_session_id(session_id)
        require_room_access(room_id, current_user["email"])
        await dm_connection_manager.connect(room_id, websocket, current_user["userId"], current_user["email"])
        await websocket.send_json({"type": "connected", "roomId": room_id})
        await mark_room_as_read_and_notify(room_id, current_user)

        while True:
            payload = await websocket.receive_json()
            if payload.get("type") != "send_message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "UNSUPPORTED_EVENT",
                        "message": "지원하지 않는 이벤트입니다.",
                    }
                )
                continue

            message_row = await create_dm_message(room_id, current_user, payload.get("content"))
            await dm_connection_manager.broadcast_message(room_id, message_row)
            connected_users = await dm_connection_manager.list_connected_users(room_id)
            for connected_user in connected_users:
                if connected_user["userEmail"] == current_user["email"]:
                    continue

                advanced = dm_model.mark_room_as_read(room_id, connected_user["userEmail"], message_row["messageId"])
                if advanced:
                    await dm_connection_manager.broadcast_event(
                        room_id,
                        {
                            "type": "messages_read",
                            "data": {
                                "roomId": room_id,
                                "readerUserId": connected_user["userId"],
                                "lastReadMessageId": message_row["messageId"],
                            },
                        },
                    )
    except APIException as exc:
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "code": exc.code,
                "message": exc.message,
            }
        )
        await websocket.close(code=4401)
    except WebSocketDisconnect:
        await dm_connection_manager.disconnect(room_id, websocket)
    except Exception:
        await dm_connection_manager.disconnect(room_id, websocket)
        raise
