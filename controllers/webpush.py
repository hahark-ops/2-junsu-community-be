import asyncio
from datetime import datetime
import json
import logging
import os

from pywebpush import WebPushException, webpush

from models import dm_model, webpush_model
from realtime.redis_bus import has_room_presence
from utils import APIException

logger = logging.getLogger("community.webpush")
MAX_PREVIEW_LENGTH = 80


def _vapid_public_key() -> str:
    return os.getenv("WEB_PUSH_VAPID_PUBLIC_KEY", "").strip()


def _vapid_private_key() -> str:
    return os.getenv("WEB_PUSH_VAPID_PRIVATE_KEY", "").strip()


def _vapid_subject() -> str:
    return os.getenv("WEB_PUSH_SUBJECT", "").strip()


def web_push_enabled() -> bool:
    return bool(_vapid_public_key() and _vapid_private_key() and _vapid_subject())


def _normalize_subscription_payload(payload: dict) -> tuple[str, str, str]:
    endpoint = str((payload or {}).get("endpoint") or "").strip()
    keys = (payload or {}).get("keys") or {}
    p256dh = str(keys.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or "").strip()

    if not endpoint or not p256dh or not auth:
        raise APIException(
            code="INVALID_PUSH_SUBSCRIPTION",
            message="유효하지 않은 푸시 구독 정보입니다.",
            status_code=400,
        )
    return endpoint, p256dh, auth


async def get_webpush_status(current_user: dict):
    active_subscription_count = webpush_model.count_active_subscriptions(current_user["email"])
    return {
        "code": "GET_WEB_PUSH_STATUS_SUCCESS",
        "message": "웹푸시 상태 조회 성공",
        "data": {
            "enabled": web_push_enabled(),
            "subscribed": active_subscription_count > 0,
            "activeSubscriptionCount": active_subscription_count,
            "vapidPublicKey": _vapid_public_key() if web_push_enabled() else None,
        },
    }


async def subscribe_webpush(current_user: dict, payload: dict):
    if not web_push_enabled():
        raise APIException(
            code="WEB_PUSH_DISABLED",
            message="웹푸시가 현재 비활성화되어 있습니다.",
            status_code=503,
        )

    endpoint, p256dh, auth = _normalize_subscription_payload(payload)
    webpush_model.upsert_subscription(current_user["email"], endpoint, p256dh, auth)
    return {
        "code": "SUBSCRIBE_WEB_PUSH_SUCCESS",
        "message": "웹푸시 구독이 등록되었습니다.",
        "data": {
            "endpoint": endpoint,
            "subscribed": True,
        },
    }


async def unsubscribe_webpush(current_user: dict, payload: dict):
    endpoint = str((payload or {}).get("endpoint") or "").strip()
    if not endpoint:
        raise APIException(
            code="INVALID_PUSH_SUBSCRIPTION",
            message="유효하지 않은 푸시 구독 정보입니다.",
            status_code=400,
        )

    deactivated = webpush_model.deactivate_subscription(current_user["email"], endpoint)
    return {
        "code": "UNSUBSCRIBE_WEB_PUSH_SUCCESS",
        "message": "웹푸시 구독이 해제되었습니다.",
        "data": {
            "endpoint": endpoint,
            "deactivated": bool(deactivated),
        },
    }


def _build_push_payload(room_id: int, sender_nickname: str, content: str, created_at) -> dict:
    preview = content.strip()
    if len(preview) > MAX_PREVIEW_LENGTH:
        preview = preview[: MAX_PREVIEW_LENGTH - 1] + "…"
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "type": "dm_message",
        "roomId": room_id,
        "senderNickname": sender_nickname,
        "messagePreview": preview,
        "createdAt": created_at,
    }


def _send_web_push(subscription: dict, payload: dict):
    webpush(
        subscription_info={
            "endpoint": subscription["endpoint"],
            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth"],
            },
        },
        data=json.dumps(payload, ensure_ascii=False),
        vapid_private_key=_vapid_private_key(),
        vapid_claims={"sub": _vapid_subject()},
        ttl=60,
    )


async def notify_absent_recipient_best_effort(room_id: int, sender_user: dict, message_row: dict):
    if not web_push_enabled():
        return

    recipient_email = dm_model.get_other_participant_email(room_id, sender_user["email"])
    if not recipient_email:
        return

    try:
        recipient_present = await has_room_presence(room_id, recipient_email)
    except Exception as exc:  # pragma: no cover - runtime infra path
        logger.warning("Presence check failed roomId=%s recipient=%s error=%s", room_id, recipient_email, exc)
        return

    if recipient_present:
        return

    subscriptions = webpush_model.list_active_subscriptions(recipient_email)
    if not subscriptions:
        return

    payload = _build_push_payload(
        room_id=room_id,
        sender_nickname=message_row.get("senderNickname") or sender_user.get("nickname") or "알 수 없는 사용자",
        content=message_row.get("content") or "",
        created_at=message_row.get("createdAt"),
    )

    for subscription in subscriptions:
        try:
            await asyncio.to_thread(_send_web_push, subscription, payload)
            webpush_model.touch_subscription(subscription["subscriptionId"])
        except WebPushException as exc:  # pragma: no cover - depends on external push service
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in {404, 410}:
                webpush_model.deactivate_endpoint(subscription["endpoint"])
            logger.warning(
                "Web push delivery failed roomId=%s endpoint=%s status=%s error=%s",
                room_id,
                subscription["endpoint"],
                status_code,
                exc,
            )
        except Exception as exc:  # pragma: no cover - runtime infra path
            logger.warning(
                "Web push delivery failed roomId=%s endpoint=%s error=%s",
                room_id,
                subscription["endpoint"],
                exc,
            )
