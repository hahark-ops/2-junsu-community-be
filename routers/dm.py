from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from controllers.dm import (
    create_dm_message,
    create_or_get_room,
    dm_connection_manager,
    get_my_rooms,
    get_room_messages,
    mark_room_as_read_and_notify,
    publish_message_created,
    require_room_access,
    serialize_message_for_user,
)
from dependencies import get_current_user, resolve_user_by_session_id
from realtime.redis_bus import RedisBusError, is_redis_ready
from utils import APIException

router = APIRouter(prefix="/v1/dm")
ws_router = APIRouter()


def _require_realtime_available():
    if not is_redis_ready():
        raise APIException(
            code="REALTIME_UNAVAILABLE",
            message="실시간 채팅이 일시적으로 사용할 수 없습니다.",
            status_code=503,
        )


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
async def get_room_messages_endpoint(
    room_id: int,
    limit: int = 50,
    beforeMessageId: int | None = None,
    user: dict = Depends(get_current_user),
):
    return await get_room_messages(room_id, user, limit=limit, before_message_id=beforeMessageId)


@ws_router.websocket("/ws/dm/{room_id}")
async def dm_websocket_endpoint(websocket: WebSocket, room_id: int):
    session_id = websocket.cookies.get("session_id")
    connected = False

    try:
        _require_realtime_available()
        current_user = resolve_user_by_session_id(session_id)
        require_room_access(room_id, current_user["email"])
        await dm_connection_manager.connect(room_id, websocket, current_user["userId"], current_user["email"])
        connected = True
        await websocket.send_json({"type": "connected", "roomId": room_id})

        while True:
            payload = await websocket.receive_json()
            payload_type = payload.get("type")
            if payload_type == "send_message":
                _require_realtime_available()
                message_row, created_new = await create_dm_message(
                    room_id,
                    current_user,
                    payload.get("content"),
                    payload.get("clientMessageId"),
                )
                if created_new:
                    await publish_message_created(room_id, message_row)
                else:
                    if message_row.get("realtimePublishedAt") is None:
                        await publish_message_created(room_id, message_row)
                    else:
                        await websocket.send_json(
                            {
                                "type": "message_created",
                                "data": serialize_message_for_user(message_row, current_user),
                            }
                        )
                continue

            if payload_type == "mark_read":
                _require_realtime_available()
                last_read_message_id = payload.get("lastReadMessageId")
                if last_read_message_id is not None:
                    try:
                        last_read_message_id = int(last_read_message_id)
                    except (TypeError, ValueError):
                        raise APIException(
                            code="INVALID_MESSAGE_ID",
                            message="유효하지 않은 메시지입니다.",
                            status_code=400,
                        )
                await mark_room_as_read_and_notify(room_id, current_user, last_read_message_id)
                continue
            if payload_type != "send_message":
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "UNSUPPORTED_EVENT",
                        "message": "지원하지 않는 이벤트입니다.",
                    }
                )
                continue
    except RedisBusError:
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "REALTIME_UNAVAILABLE",
                    "message": "실시간 채팅이 일시적으로 사용할 수 없습니다.",
                }
            )
            await websocket.close(code=1013)
    except APIException as exc:
        if websocket.application_state == WebSocketState.CONNECTING:
            await websocket.accept()
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": exc.code,
                    "message": exc.message,
                }
            )
            await websocket.close(code=1013 if exc.status_code >= 500 else 4401)
    except WebSocketDisconnect:
        pass
    except Exception:
        raise
    finally:
        if connected:
            await dm_connection_manager.disconnect(room_id, websocket)
