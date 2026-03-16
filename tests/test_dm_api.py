from __future__ import annotations


def test_create_dm_room_rejects_self_chat(client, override_current_user, auth_user):
    override_current_user(auth_user)

    response = client.post("/v1/dm/rooms", json={"targetUserId": auth_user["userId"]})

    assert response.status_code == 400
    assert response.json()["code"] == "CANNOT_CHAT_WITH_SELF"


def test_get_room_messages_success(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setattr("controllers.dm.require_room_access", lambda room_id, email: {"roomId": room_id})
    monkeypatch.setattr(
        "controllers.dm.dm_model.list_messages",
        lambda room_id, limit=50, before_message_id=None: (
            [
                {
                    "messageId": 11,
                    "roomId": room_id,
                    "clientMessageId": "client-1",
                    "senderUserId": 2,
                    "senderNickname": "partner",
                    "senderProfileImage": None,
                    "senderEmail": "partner@example.com",
                    "content": "안녕하세요",
                    "createdAt": "2026-03-16 10:00:00",
                }
            ],
            False,
            11,
        ),
    )
    monkeypatch.setattr("controllers.dm.dm_model.get_partner_last_read_message_id", lambda room_id, email: 0)

    response = client.get("/v1/dm/rooms/5/messages")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["roomId"] == 5
    assert body["data"]["messages"][0]["messageId"] == 11
    assert body["data"]["oldestMessageId"] == 11


def test_websocket_send_message_returns_ack_for_existing_message(monkeypatch):
    from main import app
    from fastapi.testclient import TestClient

    current_user = {
        "userId": 1,
        "email": "tester@example.com",
        "nickname": "tester",
        "profileimage": None,
    }

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("main.start_room_event_subscriber", _noop)
    monkeypatch.setattr("main.stop_room_event_subscriber", _noop)
    monkeypatch.setattr("routers.dm.is_redis_ready", lambda: True)
    monkeypatch.setattr("routers.dm.resolve_user_by_session_id", lambda session_id: current_user)
    monkeypatch.setattr("routers.dm.require_room_access", lambda room_id, email: {"roomId": room_id})
    monkeypatch.setattr("routers.dm.set_room_presence", _noop)
    monkeypatch.setattr("routers.dm.clear_room_presence", _noop)
    monkeypatch.setattr("routers.dm.refresh_room_presence", _noop)

    async def _create_dm_message(room_id, user, content, client_message_id):
        return (
            {
                "messageId": 21,
                "roomId": room_id,
                "clientMessageId": client_message_id,
                "senderUserId": user["userId"],
                "senderNickname": user["nickname"],
                "senderProfileImage": None,
                "senderEmail": user["email"],
                "content": content,
                "createdAt": "2026-03-16 10:00:00",
                "realtimePublishedAt": "2026-03-16 10:00:01",
            },
            False,
        )

    monkeypatch.setattr("routers.dm.create_dm_message", _create_dm_message)
    monkeypatch.setattr("routers.dm.publish_dm_message_and_notify_absent", _noop)
    monkeypatch.setattr("controllers.dm.dm_model.get_partner_last_read_message_id", lambda room_id, email: 0)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/dm/9", cookies={"session_id": "valid"}) as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connected"

            websocket.send_json(
                {
                    "type": "send_message",
                    "content": "hello",
                    "clientMessageId": "client-1",
                }
            )

            payload = websocket.receive_json()
            assert payload["type"] == "message_created"
            assert payload["data"]["clientMessageId"] == "client-1"
            assert payload["data"]["isMine"] is True


def test_websocket_returns_error_when_realtime_unavailable(monkeypatch):
    from main import app
    from fastapi.testclient import TestClient

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("main.start_room_event_subscriber", _noop)
    monkeypatch.setattr("main.stop_room_event_subscriber", _noop)
    monkeypatch.setattr("routers.dm.is_redis_ready", lambda: False)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/dm/3") as websocket:
            error_payload = websocket.receive_json()
            assert error_payload["code"] == "REALTIME_UNAVAILABLE"
