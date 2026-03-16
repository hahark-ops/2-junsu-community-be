from __future__ import annotations

import asyncio


def test_webpush_status_returns_enabled_state(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.setenv("WEB_PUSH_VAPID_PUBLIC_KEY", "public-key")
    monkeypatch.setenv("WEB_PUSH_VAPID_PRIVATE_KEY", "private-key")
    monkeypatch.setenv("WEB_PUSH_SUBJECT", "mailto:test@example.com")
    monkeypatch.setattr("controllers.webpush.webpush_model.count_active_subscriptions", lambda email: 2)

    response = client.get("/v1/notifications/webpush/status")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["enabled"] is True
    assert body["data"]["activeSubscriptionCount"] == 2


def test_webpush_subscribe_requires_enabled_service(client, override_current_user, auth_user, monkeypatch):
    override_current_user(auth_user)
    monkeypatch.delenv("WEB_PUSH_VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("WEB_PUSH_VAPID_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("WEB_PUSH_SUBJECT", raising=False)

    response = client.post(
        "/v1/notifications/webpush/subscribe",
        json={"endpoint": "https://example.com", "keys": {"p256dh": "key", "auth": "auth"}},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "WEB_PUSH_DISABLED"


def test_webpush_unsubscribe_requires_endpoint(client, override_current_user, auth_user):
    override_current_user(auth_user)

    response = client.request("DELETE", "/v1/notifications/webpush/subscribe", json={})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PUSH_SUBSCRIPTION"


def test_notify_absent_recipient_best_effort_touches_subscription(monkeypatch):
    from controllers import webpush

    monkeypatch.setenv("WEB_PUSH_VAPID_PUBLIC_KEY", "public-key")
    monkeypatch.setenv("WEB_PUSH_VAPID_PRIVATE_KEY", "private-key")
    monkeypatch.setenv("WEB_PUSH_SUBJECT", "mailto:test@example.com")
    monkeypatch.setattr("controllers.webpush.dm_model.get_other_participant_email", lambda room_id, email: "target@example.com")

    async def _not_present(room_id, email):
        return False

    touched = {}

    monkeypatch.setattr("controllers.webpush.has_room_presence", _not_present)
    monkeypatch.setattr(
        "controllers.webpush.webpush_model.list_active_subscriptions",
        lambda email: [
            {
                "subscriptionId": 1,
                "endpoint": "https://example.com/sub",
                "p256dh": "key",
                "auth": "auth",
            }
        ],
    )
    monkeypatch.setattr("controllers.webpush.webpush_model.touch_subscription", lambda subscription_id: touched.setdefault("id", subscription_id))

    async def _to_thread(func, *args, **kwargs):
        return None

    monkeypatch.setattr("controllers.webpush.asyncio.to_thread", _to_thread)

    asyncio.run(
        webpush.notify_absent_recipient_best_effort(
            3,
            {"email": "sender@example.com", "nickname": "sender"},
            {"content": "새 메시지", "senderNickname": "sender", "createdAt": "2026-03-16T10:00:00"},
        )
    )

    assert touched["id"] == 1
