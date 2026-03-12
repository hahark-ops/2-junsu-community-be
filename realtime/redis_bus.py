import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable

import redis.asyncio as redis


DM_CHANNEL_PREFIX = os.getenv("DM_CHANNEL_PREFIX", "dm.room")
REDIS_URL = os.getenv("REDIS_URL")

_pub_client: redis.Redis | None = None
_sub_client: redis.Redis | None = None
_subscriber_task: asyncio.Task | None = None
_ready = False
_handler: Callable[[int, dict], Awaitable[None]] | None = None
_last_subscriber_heartbeat_at = 0.0
_last_subscriber_error = ""
_last_publisher_error = ""
_startup_event: asyncio.Event | None = None
_subscriber_started_once = False


class RedisBusError(RuntimeError):
    pass


async def ensure_redis_ready() -> None:
    if not REDIS_URL:
        raise RedisBusError("REDIS_URL is required for DM realtime delivery")

    global _pub_client, _last_publisher_error
    if _pub_client is None:
        _pub_client = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        await _pub_client.ping()
        _last_publisher_error = ""
    except Exception as exc:  # pragma: no cover - runtime infra path
        _last_publisher_error = str(exc)
        _mark_unready(str(exc))
        raise RedisBusError(f"Redis connection failed: {exc}") from exc


def _mark_ready() -> None:
    global _ready, _last_subscriber_heartbeat_at, _last_subscriber_error, _subscriber_started_once
    _ready = True
    _subscriber_started_once = True
    _last_subscriber_heartbeat_at = time.time()
    _last_subscriber_error = ""


def _mark_unready(error: str = "") -> None:
    global _ready, _last_subscriber_error
    _ready = False
    _last_subscriber_error = error


def is_redis_ready() -> bool:
    if not REDIS_URL:
        return False
    if not _ready:
        return False
    if _subscriber_task is None or _subscriber_task.done():
        return False
    return True


def get_redis_status() -> dict:
    return {
        "enabled": bool(REDIS_URL),
        "publisherReady": _pub_client is not None,
        "subscriberRunning": _subscriber_task is not None and not _subscriber_task.done(),
        "ready": is_redis_ready(),
        "lastSubscriberHeartbeatAt": _last_subscriber_heartbeat_at or None,
        "lastSubscriberError": _last_subscriber_error or None,
        "lastPublisherError": _last_publisher_error or None,
    }


async def get_redis_status_async() -> dict:
    status = get_redis_status()
    publisher_healthy = False
    if REDIS_URL:
        try:
            await ensure_redis_ready()
            publisher_healthy = True
        except RedisBusError:
            publisher_healthy = False
        status = get_redis_status()
    status["publisherHealthy"] = publisher_healthy
    status["ready"] = bool(status["subscriberRunning"] and publisher_healthy and status["ready"])
    return status


def room_channel(room_id: int) -> str:
    return f"{DM_CHANNEL_PREFIX}.{room_id}"


async def publish_room_event(room_id: int, payload: dict) -> None:
    if not is_redis_ready():
        raise RedisBusError("Redis realtime subscriber is unavailable")
    if _pub_client is None:
        await ensure_redis_ready()
    await _pub_client.publish(room_channel(room_id), json.dumps(payload, ensure_ascii=False))


async def _subscriber_loop() -> None:
    global _sub_client
    assert _handler is not None
    while True:
        pubsub = None
        try:
            _sub_client = redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = _sub_client.pubsub()
            await pubsub.psubscribe(f"{DM_CHANNEL_PREFIX}.*")
            _mark_ready()
            if _startup_event is not None and not _startup_event.is_set():
                _startup_event.set()

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=False, timeout=1.0)
                _mark_ready()
                if not message or message.get("type") != "pmessage":
                    continue

                channel = message.get("channel") or ""
                data = message.get("data")
                if not channel or data is None:
                    continue

                try:
                    room_id = int(channel.rsplit(".", 1)[-1])
                    payload = json.loads(data)
                except Exception:
                    continue

                await _handler(room_id, payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - runtime infra path
            _mark_unready(str(exc))
            if _startup_event is not None and not _startup_event.is_set():
                _startup_event.set()
            await asyncio.sleep(1)
        finally:
            if pubsub is not None:
                try:
                    await pubsub.punsubscribe(f"{DM_CHANNEL_PREFIX}.*")
                except Exception:
                    pass
                try:
                    await pubsub.close()
                except Exception:
                    pass
            if _sub_client is not None:
                try:
                    await _sub_client.close()
                except Exception:
                    pass
                _sub_client = None


async def start_room_event_subscriber(handler: Callable[[int, dict], Awaitable[None]]) -> None:
    global _handler, _subscriber_task, _startup_event
    if not REDIS_URL:
        raise RedisBusError("REDIS_URL is required for DM realtime delivery")
    _handler = handler
    if _subscriber_task is not None and not _subscriber_task.done():
        return
    _startup_event = asyncio.Event()
    _subscriber_task = asyncio.create_task(_subscriber_loop(), name="dm-redis-subscriber")
    try:
        await asyncio.wait_for(_startup_event.wait(), timeout=5)
    finally:
        _startup_event = None


async def stop_room_event_subscriber() -> None:
    global _subscriber_task, _pub_client, _startup_event
    _mark_unready()
    _startup_event = None

    if _subscriber_task is not None:
        _subscriber_task.cancel()
        try:
            await _subscriber_task
        except asyncio.CancelledError:
            pass
        _subscriber_task = None

    if _pub_client is not None:
        await _pub_client.close()
        _pub_client = None
