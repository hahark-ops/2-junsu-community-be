import asyncio
import logging
from collections import defaultdict
from datetime import datetime

import mysql.connector

from models import dm_model, user_model
from realtime.redis_bus import publish_room_event
from utils import APIException

MAX_DM_MESSAGE_LENGTH = 500
logger = logging.getLogger("community.dm")


def _serialize_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return value


def _serialize_room_row(row: dict) -> dict:
    return {
        "roomId": row["roomId"],
        "partner": {
            "userId": row.get("partnerUserId"),
            "nickname": row.get("partnerNickname"),
            "profileImage": row.get("partnerProfileImage"),
        },
        "lastMessage": row.get("lastMessage"),
        "lastMessageAt": _serialize_datetime(row.get("lastMessageAt")),
        "unreadCount": int(row.get("unreadCount") or 0),
    }


def serialize_message_row(
    row: dict,
    current_user_id: int,
    current_user_email: str,
    partner_last_read_message_id: int | None = None,
) -> dict:
    sender_user_id = row.get("senderUserId")
    sender_email = row.get("senderEmail")
    message_id = row.get("messageId")
    read_by_other = False
    if sender_email == current_user_email and partner_last_read_message_id is not None:
        read_by_other = int(message_id or 0) <= int(partner_last_read_message_id)
    return {
        "messageId": message_id,
        "roomId": row.get("roomId"),
        "senderUserId": sender_user_id,
        "senderNickname": row.get("senderNickname"),
        "senderProfileImage": row.get("senderProfileImage"),
        "content": row.get("content"),
        "createdAt": _serialize_datetime(row.get("createdAt")),
        "isMine": str(sender_user_id) == str(current_user_id),
        "readByOther": read_by_other,
    }


def _validate_message_content(content: str | None) -> str:
    if content is None:
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="메시지 내용은 필수입니다.", status_code=400)

    normalized = str(content).strip()
    if not normalized:
        raise APIException(code="REQUIRED_FIELDS_MISSING", message="메시지 내용은 필수입니다.", status_code=400)
    if len(normalized) > MAX_DM_MESSAGE_LENGTH:
        raise APIException(
            code="MESSAGE_TOO_LONG",
            message=f"메시지는 최대 {MAX_DM_MESSAGE_LENGTH}자까지 입력할 수 있습니다.",
            status_code=400,
        )
    return normalized


async def create_or_get_room(target_user_id: int, current_user: dict):
    if current_user["userId"] == target_user_id:
        raise APIException(code="CANNOT_CHAT_WITH_SELF", message="본인과는 채팅할 수 없습니다.", status_code=400)

    target_user = user_model.get_user_by_id(target_user_id)
    if not target_user:
        raise APIException(code="USER_NOT_FOUND", message="채팅할 사용자를 찾을 수 없습니다.", status_code=404)

    if target_user.get("is_deleted"):
        raise APIException(code="USER_NOT_FOUND", message="채팅할 사용자를 찾을 수 없습니다.", status_code=404)

    room = dm_model.get_room_by_participants(current_user["email"], target_user["email"])
    if not room:
        try:
            room_id = dm_model.create_room(current_user["email"], target_user["email"])
        except mysql.connector.IntegrityError as exc:
            if getattr(exc, "errno", None) == 1062:
                room = dm_model.get_room_by_participants(current_user["email"], target_user["email"])
                if not room:
                    raise
                room_id = room["roomId"]
            else:
                raise
        room = dm_model.get_room_by_id(room_id)

    room_list_row = {
        "roomId": room["roomId"],
        "partnerUserId": target_user["userId"],
        "partnerNickname": target_user["nickname"],
        "partnerProfileImage": target_user.get("profileimage"),
        "lastMessage": None,
        "lastMessageAt": None,
    }

    return {
        "code": "DM_ROOM_READY",
        "message": "채팅방이 준비되었습니다.",
        "data": _serialize_room_row(room_list_row),
    }


async def get_my_rooms(current_user: dict):
    rooms = dm_model.list_rooms_for_user(current_user["email"])
    return {
        "code": "GET_DM_ROOMS_SUCCESS",
        "message": "채팅방 목록 조회 성공",
        "data": {
            "rooms": [_serialize_room_row(row) for row in rooms],
            "totalUnreadCount": sum(int(row.get("unreadCount") or 0) for row in rooms),
        },
    }


async def get_room_messages(room_id: int, current_user: dict, limit: int = 50, before_message_id: int | None = None):
    require_room_access(room_id, current_user["email"])
    rows, has_more, oldest_message_id = dm_model.list_messages(room_id, limit=limit, before_message_id=before_message_id)
    partner_last_read_message_id = dm_model.get_partner_last_read_message_id(room_id, current_user["email"])
    await mark_room_as_read_and_notify(room_id, current_user)
    return {
        "code": "GET_DM_MESSAGES_SUCCESS",
        "message": "메시지 목록 조회 성공",
        "data": {
            "roomId": room_id,
            "messages": [
                serialize_message_row(row, current_user["userId"], current_user["email"], partner_last_read_message_id)
                for row in rows
            ],
            "hasMore": has_more,
            "oldestMessageId": oldest_message_id,
        },
    }


def require_room_access(room_id: int, user_email: str):
    room = dm_model.get_room_by_id(room_id)
    if not room:
        raise APIException(code="DM_ROOM_NOT_FOUND", message="채팅방을 찾을 수 없습니다.", status_code=404)
    if not dm_model.is_room_participant(room_id, user_email):
        raise APIException(code="DM_ROOM_FORBIDDEN", message="해당 채팅방에 접근할 수 없습니다.", status_code=403)
    return room


class DMConnectionManager:
    def __init__(self):
        self._connections: dict[int, dict] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def connect(self, room_id: int, websocket, user_id: int, user_email: str):
        await websocket.accept()
        async with self._lock:
            self._connections[room_id][websocket] = {
                "userId": user_id,
                "userEmail": user_email,
            }

    async def disconnect(self, room_id: int, websocket):
        async with self._lock:
            room_connections = self._connections.get(room_id)
            if not room_connections:
                return
            room_connections.pop(websocket, None)
            if not room_connections:
                self._connections.pop(room_id, None)

    async def broadcast_message(self, room_id: int, message_row: dict):
        async with self._lock:
            targets = list(self._connections.get(room_id, {}).items())

        stale = []
        for websocket, connection in targets:
            try:
                await websocket.send_json(
                    {
                        "type": "message_created",
                        "data": serialize_message_row(
                            message_row,
                            connection["userId"],
                            connection["userEmail"],
                        ),
                    }
                )
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(room_id, websocket)

    async def broadcast_event(self, room_id: int, payload: dict):
        async with self._lock:
            targets = list(self._connections.get(room_id, {}).keys())

        stale = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            await self.disconnect(room_id, websocket)

    async def list_connected_users(self, room_id: int):
        async with self._lock:
            return list(self._connections.get(room_id, {}).values())

    async def list_connection_targets(self, room_id: int):
        async with self._lock:
            return list(self._connections.get(room_id, {}).items())


dm_connection_manager = DMConnectionManager()


async def create_dm_message(room_id: int, current_user: dict, content: str) -> dict:
    require_room_access(room_id, current_user["email"])
    message_content = _validate_message_content(content)
    message_id = dm_model.create_message(room_id, current_user["email"], message_content)
    return dm_model.get_message_by_id(message_id)


async def mark_room_as_read_and_notify(room_id: int, current_user: dict):
    last_message_id = dm_model.get_room_last_message_id(room_id)
    if not last_message_id:
        return None

    advanced = dm_model.mark_room_as_read(room_id, current_user["email"], last_message_id)
    if not advanced:
        return None

    payload = {
        "type": "messages_read",
        "data": {
            "roomId": room_id,
            "readerUserId": current_user["userId"],
            "lastReadMessageId": last_message_id,
        },
    }
    await publish_room_event(room_id, payload)
    return payload


async def publish_message_created(room_id: int, message_row: dict):
    payload = {
        "type": "message_created",
        "data": {
            "messageId": message_row.get("messageId"),
            "roomId": message_row.get("roomId"),
            "senderUserId": message_row.get("senderUserId"),
            "senderNickname": message_row.get("senderNickname"),
            "senderProfileImage": message_row.get("senderProfileImage"),
            "senderEmail": message_row.get("senderEmail"),
            "content": message_row.get("content"),
            "createdAt": _serialize_datetime(message_row.get("createdAt")),
        },
    }
    await publish_room_event(room_id, payload)


def _serialize_payload_for_connection(payload: dict, current_connection: dict) -> dict:
    if payload.get("type") != "message_created":
        return payload

    data = dict(payload.get("data") or {})
    data["isMine"] = data.get("senderEmail") == current_connection["userEmail"]
    data["readByOther"] = False
    data.pop("senderEmail", None)
    return {"type": "message_created", "data": data}


async def _maybe_mark_local_room_as_read(room_id: int, payload: dict):
    if payload.get("type") != "message_created":
        return

    data = payload.get("data") or {}
    sender_email = data.get("senderEmail")
    message_id = data.get("messageId")
    sender_user_id = data.get("senderUserId")
    if not sender_email or not message_id:
        return

    connected_users = await dm_connection_manager.list_connected_users(room_id)
    for connected_user in connected_users:
        if connected_user["userEmail"] == sender_email:
            continue

        advanced = dm_model.mark_room_as_read(room_id, connected_user["userEmail"], int(message_id))
        if not advanced:
            continue

        await publish_room_event(
            room_id,
            {
                "type": "messages_read",
                "data": {
                    "roomId": room_id,
                    "readerUserId": connected_user["userId"],
                    "lastReadMessageId": int(message_id),
                    "senderUserId": sender_user_id,
                },
            },
        )


async def handle_room_event(room_id: int, payload: dict):
    if payload.get("type") != "message_created":
        await dm_connection_manager.broadcast_event(room_id, payload)
        return

    targets = await dm_connection_manager.list_connection_targets(room_id)
    stale = []
    for websocket, connection in targets:
        try:
            await websocket.send_json(_serialize_payload_for_connection(payload, connection))
        except Exception:
            stale.append(websocket)

    for websocket in stale:
        await dm_connection_manager.disconnect(room_id, websocket)

    await _maybe_mark_local_room_as_read(room_id, payload)
