import asyncio
import json
import os
from collections.abc import Awaitable, Callable

import redis.asyncio as redis


DM_CHANNEL_PREFIX = os.getenv("DM_CHANNEL_PREFIX", "dm.room")
REDIS_URL = os.getenv("REDIS_URL")

_pub_client: redis.Redis | None = None
_sub_client: redis.Redis | None = None
_subscriber_task: asyncio.Task | None = None
_ready = False
_handler: Callable[[int, dict], Awaitable[None]] | None = None


class RedisBusError(RuntimeError):
    pass


async def ensure_redis_ready() -> None:
    if not REDIS_URL:
        raise RedisBusError("REDIS_URL is required for DM realtime delivery")

    global _pub_client
    if _pub_client is None:
        _pub_client = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        await _pub_client.ping()
    except Exception as exc:  # pragma: no cover - runtime infra path
        raise RedisBusError(f"Redis connection failed: {exc}") from exc


def is_redis_ready() -> bool:
    return _ready


def room_channel(room_id: int) -> str:
    return f"{DM_CHANNEL_PREFIX}.{room_id}"


async def publish_room_event(room_id: int, payload: dict) -> None:
    if _pub_client is None:
        await ensure_redis_ready()
    await _pub_client.publish(room_channel(room_id), json.dumps(payload, ensure_ascii=False))


async def _subscriber_loop() -> None:
    global _sub_client
    assert _handler is not None
    _sub_client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = _sub_client.pubsub()
    await pubsub.psubscribe(f"{DM_CHANNEL_PREFIX}.*")

    try:
        async for message in pubsub.listen():
            if message.get("type") != "pmessage":
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
    finally:
        try:
            await pubsub.punsubscribe(f"{DM_CHANNEL_PREFIX}.*")
        finally:
            await pubsub.close()
            await _sub_client.close()
            _sub_client = None


async def start_room_event_subscriber(handler: Callable[[int, dict], Awaitable[None]]) -> None:
    global _handler, _subscriber_task, _ready
    await ensure_redis_ready()
    _handler = handler
    _subscriber_task = asyncio.create_task(_subscriber_loop(), name="dm-redis-subscriber")
    _ready = True


async def stop_room_event_subscriber() -> None:
    global _subscriber_task, _pub_client, _ready
    _ready = False

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
