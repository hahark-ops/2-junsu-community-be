from __future__ import annotations

import asyncio

import pytest
from fastapi import Response

from utils import APIException


def run(coro):
    return asyncio.run(coro)


def test_check_email_availability_success(monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_email", lambda email: 0)

    payload = run(__import__("controllers.auth", fromlist=[""]).check_email_availability("new@example.com"))

    assert payload["code"] == "EMAIL_AVAILABLE"


def test_check_email_availability_invalid(monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_email", lambda email: 0)

    with pytest.raises(APIException) as exc:
        run(__import__("controllers.auth", fromlist=[""]).check_email_availability("bad-email"))

    assert exc.value.code == "INVALID_EMAIL_FORMAT"


def test_check_nickname_availability_duplicate(monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_nickname", lambda nickname: 1)

    with pytest.raises(APIException) as exc:
        run(__import__("controllers.auth", fromlist=[""]).check_nickname_availability("tester"))

    assert exc.value.code == "ALREADY_EXIST_NICKNAME"


def test_auth_signup_weak_password(monkeypatch):
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_email", lambda email: 0)
    monkeypatch.setattr("controllers.auth.auth_model.count_users_by_nickname", lambda nickname: 0)

    with pytest.raises(APIException) as exc:
        run(
            __import__("controllers.auth", fromlist=[""]).auth_signup(
                {"email": "user@example.com", "password": "weak", "nickname": "tester"}
            )
        )

    assert exc.value.code == "WEAK_PASSWORD"


def test_auth_logout_deletes_session_cookie(monkeypatch):
    deleted = {}

    def _delete(session_id):
        deleted["session_id"] = session_id

    monkeypatch.setattr("controllers.auth.auth_model.delete_session", _delete)
    response = Response()

    payload = run(__import__("controllers.auth", fromlist=[""]).auth_logout(response, "session-1"))

    assert payload["code"] == "LOGOUT_SUCCESS"
    assert deleted["session_id"] == "session-1"
    assert "session_id=" in response.headers["set-cookie"]


def test_create_post_success(monkeypatch):
    monkeypatch.setattr("controllers.post.post_model.create_post", lambda **kwargs: 10)

    payload = run(
        __import__("controllers.post", fromlist=[""]).create_post(
            {"title": "title", "content": "body"},
            {"nickname": "tester", "email": "tester@example.com"},
        )
    )

    assert payload["data"]["postId"] == 10


def test_get_post_detail_increments_view(monkeypatch):
    controller = __import__("controllers.post", fromlist=[""])
    calls = {"count": 0}

    def _detail(post_id):
        calls["count"] += 1
        return {
            "postId": post_id,
            "title": "title",
            "content": "body",
            "fileUrl": None,
            "writer": "tester",
            "viewCount": calls["count"] - 1,
            "createdAt": "2026-03-16 10:00:00",
            "authorProfileImage": None,
            "authorId": 1,
        }

    monkeypatch.setattr("controllers.post.post_model.get_post_detail", _detail)
    monkeypatch.setattr("controllers.post.post_model.increment_view_count", lambda post_id: None)
    monkeypatch.setattr("controllers.post.post_model.count_likes", lambda post_id: 0)
    monkeypatch.setattr("controllers.post.post_model.count_comments", lambda post_id: 0)
    monkeypatch.setattr("controllers.post.post_model.fetch_likes", lambda post_id: [])

    payload = run(controller.get_post_detail(3, increase_view=True))

    assert payload["data"]["viewCount"] == 1


def test_delete_post_forbidden(monkeypatch):
    monkeypatch.setattr(
        "controllers.post.post_model.get_post_by_id",
        lambda post_id: {"postId": post_id, "writerEmail": "other@example.com"},
    )

    with pytest.raises(APIException) as exc:
        run(__import__("controllers.post", fromlist=[""]).delete_post(1, {"email": "me@example.com"}))

    assert exc.value.code == "NOT_THE_AUTHOR"


def test_unlike_post_success(monkeypatch):
    monkeypatch.setattr("controllers.post.post_model.exists_post", lambda post_id: True)
    monkeypatch.setattr("controllers.post.post_model.remove_like", lambda post_id, email: None)
    monkeypatch.setattr("controllers.post.post_model.count_likes", lambda post_id: 3)

    payload = run(__import__("controllers.post", fromlist=[""]).unlike_post(8, {"email": "me@example.com"}))

    assert payload["data"]["totalLikeCount"] == 3
    assert payload["data"]["isLiked"] is False


def test_create_comment_post_not_found(monkeypatch):
    monkeypatch.setattr("controllers.comment.post_model.exists_post", lambda post_id: False)

    with pytest.raises(APIException) as exc:
        run(
            __import__("controllers.comment", fromlist=[""]).create_comment(
                1,
                {"content": "hello"},
                {"nickname": "tester", "email": "tester@example.com"},
            )
        )

    assert exc.value.code == "POST_NOT_FOUND"


def test_create_comment_success(monkeypatch):
    monkeypatch.setattr("controllers.comment.post_model.exists_post", lambda post_id: True)
    monkeypatch.setattr("controllers.comment.comment_model.create_comment", lambda **kwargs: 7)

    payload = run(
        __import__("controllers.comment", fromlist=[""]).create_comment(
            1,
            {"content": "hello"},
            {"nickname": "tester", "email": "tester@example.com", "userId": 2, "profileimage": None},
        )
    )

    assert payload["data"]["commentId"] == 7


def test_get_comments_formats_rows(monkeypatch):
    monkeypatch.setattr(
        "controllers.comment.comment_model.fetch_comments",
        lambda post_id: [
            {
                "commentId": 1,
                "postId": post_id,
                "content": "hello",
                "writer": "tester",
                "createdAt": "2026-03-16 10:00:00",
                "updatedAt": None,
                "authorProfileImage": None,
                "authorId": 3,
                "authorNickname": "tester",
            }
        ],
    )

    payload = run(__import__("controllers.comment", fromlist=[""]).get_comments(4))

    assert payload["data"][0]["nickname"] == "tester"


def test_delete_comment_forbidden(monkeypatch):
    monkeypatch.setattr(
        "controllers.comment.comment_model.get_comment",
        lambda comment_id, post_id: {"writerEmail": "other@example.com"},
    )

    with pytest.raises(APIException) as exc:
        run(
            __import__("controllers.comment", fromlist=[""]).delete_comment(
                1, 2, {"email": "me@example.com"}
            )
        )

    assert exc.value.code == "NOT_THE_COMMENT_AUTHOR"


def test_get_my_info_success():
    payload = run(
        __import__("controllers.user", fromlist=[""]).get_my_info(
            {"userId": 1, "email": "me@example.com", "nickname": "me", "profileimage": None}
        )
    )

    assert payload["data"]["email"] == "me@example.com"


def test_get_user_by_id_forbidden():
    with pytest.raises(APIException) as exc:
        run(__import__("controllers.user", fromlist=[""]).get_user_by_id(2, {"userId": 1}))

    assert exc.value.code == "PERMISSION_DENIED"


def test_update_user_invalid_nickname(monkeypatch):
    monkeypatch.setattr("controllers.user.user_model.get_user_by_id", lambda user_id: {"userId": user_id, "email": "me@example.com"})

    with pytest.raises(APIException) as exc:
        run(
            __import__("controllers.user", fromlist=[""]).update_user(
                1,
                {"nickname": "bad nick"},
                {"userId": 1},
            )
        )

    assert exc.value.code == "INVALID_NICKNAME_FORMAT"


def test_update_user_profile_image_success(monkeypatch):
    monkeypatch.setattr("controllers.user.user_model.get_user_by_id", lambda user_id: {"userId": user_id, "email": "me@example.com"})
    monkeypatch.setattr("controllers.user.user_model.update_user_profile_with_writer_sync", lambda **kwargs: None)

    payload = run(
        __import__("controllers.user", fromlist=[""]).update_user(
            1,
            {"profileImage": "/uploads/me.png"},
            {"userId": 1},
        )
    )

    assert payload["code"] == "UPDATE_USER_SUCCESS"


def test_change_password_success(monkeypatch):
    monkeypatch.setattr(
        "controllers.user.user_model.get_user_by_id",
        lambda user_id: {"userId": user_id, "password": "$2b$12$VbR3W0n.0e1LtkWxppI9MefJSPdZRhqUWLWyd4InENcy9XUG6uH2K"},
    )
    monkeypatch.setattr("controllers.user.verify_password", lambda current_pw, stored_pw: True)
    updated = {}
    monkeypatch.setattr("controllers.user.user_model.update_user_password", lambda user_id, password_hash: updated.update({"user_id": user_id}))

    payload = run(
        __import__("controllers.user", fromlist=[""]).change_password(
            1,
            {"currentPassword": "Old!1234", "newPassword": "New!12345Aa"},
            {"userId": 1},
        )
    )

    assert payload["code"] == "CHANGE_PASSWORD_SUCCESS"
    assert updated["user_id"] == 1


def test_dm_create_or_get_room_success(monkeypatch):
    controller = __import__("controllers.dm", fromlist=[""])
    monkeypatch.setattr("controllers.dm.user_model.get_user_by_id", lambda user_id: {"userId": user_id, "email": "target@example.com", "nickname": "target", "profileimage": None})
    monkeypatch.setattr("controllers.dm.dm_model.get_room_by_participants", lambda a, b: None)
    monkeypatch.setattr("controllers.dm.dm_model.create_room", lambda a, b: 9)
    monkeypatch.setattr("controllers.dm.dm_model.get_room_by_id", lambda room_id: {"roomId": room_id})

    payload = run(controller.create_or_get_room(2, {"userId": 1, "email": "me@example.com"}))

    assert payload["data"]["roomId"] == 9


def test_dm_get_my_rooms_sums_unread(monkeypatch):
    monkeypatch.setattr(
        "controllers.dm.dm_model.list_rooms_for_user",
        lambda email: [
            {"roomId": 1, "partnerUserId": 2, "partnerNickname": "a", "partnerProfileImage": None, "lastMessage": "x", "lastMessageAt": None, "unreadCount": 2},
            {"roomId": 2, "partnerUserId": 3, "partnerNickname": "b", "partnerProfileImage": None, "lastMessage": "y", "lastMessageAt": None, "unreadCount": 1},
        ],
    )

    payload = run(__import__("controllers.dm", fromlist=[""]).get_my_rooms({"email": "me@example.com"}))

    assert payload["data"]["totalUnreadCount"] == 3


def test_dm_validate_message_content_and_client_message_id():
    controller = __import__("controllers.dm", fromlist=[""])

    assert controller._validate_message_content("  hi  ") == "hi"
    assert controller._validate_client_message_id("  client-1  ") == "client-1"

    with pytest.raises(APIException):
        controller._validate_message_content("   ")
    with pytest.raises(APIException):
        controller._validate_client_message_id("")


def test_mark_room_as_read_and_notify_invalid_message(monkeypatch):
    monkeypatch.setattr("controllers.dm.require_room_access", lambda room_id, email: {"roomId": room_id})
    monkeypatch.setattr("controllers.dm.dm_model.get_message_by_id", lambda message_id: None)

    with pytest.raises(APIException) as exc:
        run(
            __import__("controllers.dm", fromlist=[""]).mark_room_as_read_and_notify(
                1,
                {"userId": 1, "email": "me@example.com"},
                99,
            )
        )

    assert exc.value.code == "INVALID_MESSAGE_ID"


def test_mark_room_as_read_and_notify_publishes(monkeypatch):
    controller = __import__("controllers.dm", fromlist=[""])
    monkeypatch.setattr("controllers.dm.require_room_access", lambda room_id, email: {"roomId": room_id})
    monkeypatch.setattr("controllers.dm.dm_model.get_room_last_message_id", lambda room_id: 5)
    monkeypatch.setattr("controllers.dm.dm_model.get_user_last_read_message_id", lambda room_id, email: 1)
    monkeypatch.setattr("controllers.dm.dm_model.mark_room_as_read", lambda room_id, email, last_read: True)
    published = {}

    async def _publish(room_id, payload):
        published["room_id"] = room_id
        published["payload"] = payload

    monkeypatch.setattr("controllers.dm.publish_room_event", _publish)

    payload = run(controller.mark_room_as_read_and_notify(1, {"userId": 1, "email": "me@example.com"}))

    assert payload["type"] == "messages_read"
    assert published["room_id"] == 1


def test_publish_message_created_marks_realtime_published(monkeypatch):
    controller = __import__("controllers.dm", fromlist=[""])
    published = {}
    marked = {}

    async def _publish(room_id, payload):
        published["room_id"] = room_id
        published["payload"] = payload

    monkeypatch.setattr("controllers.dm.publish_room_event", _publish)
    monkeypatch.setattr("controllers.dm.dm_model.mark_message_realtime_published", lambda message_id: marked.update({"message_id": message_id}))

    run(
        controller.publish_message_created(
            1,
            {
                "messageId": 10,
                "roomId": 1,
                "clientMessageId": "client-1",
                "senderUserId": 2,
                "senderNickname": "tester",
                "senderProfileImage": None,
                "senderEmail": "tester@example.com",
                "content": "hello",
                "createdAt": "2026-03-16 10:00:00",
            },
        )
    )

    assert published["payload"]["type"] == "message_created"
    assert marked["message_id"] == 10


def test_handle_room_event_non_message_uses_broadcast(monkeypatch):
    controller = __import__("controllers.dm", fromlist=[""])
    called = {}

    async def _broadcast(room_id, payload):
        called["room_id"] = room_id
        called["payload"] = payload

    monkeypatch.setattr("controllers.dm.dm_connection_manager.broadcast_event", _broadcast)

    run(controller.handle_room_event(3, {"type": "messages_read", "data": {"roomId": 3}}))

    assert called["room_id"] == 3

