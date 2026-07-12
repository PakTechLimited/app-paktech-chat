import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def publish_message(room_id: int, event: dict) -> None:
    client = await get_redis()
    channel = f"room:{room_id}"
    await client.publish(channel, json.dumps(event))
    logger.debug("Published to %s: %s", channel, event)


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
