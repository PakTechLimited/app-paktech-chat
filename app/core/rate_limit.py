"""Fixed-window rate limiting backed by Redis (shared across all pods).

Each limiter is a counter key with a TTL equal to the window. The first hit
creates the key with the TTL (SET NX EX) and every hit increments it, both in
one transaction, so a key can never be left without an expiry.

Fails OPEN: if Redis is unreachable we log and allow the request rather than
locking every user out of login. Brute-force protection degrades, the app
stays up.
"""

import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.services.redis_service import get_redis

logger = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    """Peer address. Behind an ingress, run uvicorn/gunicorn with the proxy's
    forwarded-allow-ips so this is the real client, not the proxy."""
    return request.client.host if request.client else "unknown"


async def enforce(key: str, limit: int, window_seconds: int) -> None:
    """Count one hit on ``key``; raise 429 once ``limit`` is exceeded."""
    if not settings.rate_limit_enabled:
        return
    try:
        r = await get_redis()
        redis_key = f"rl:{key}"
        async with r.pipeline(transaction=True) as pipe:
            pipe.set(redis_key, 0, ex=window_seconds, nx=True)
            pipe.incr(redis_key)
            pipe.ttl(redis_key)
            _, count, ttl = await pipe.execute()
    except Exception:  # noqa: BLE001 - deliberate fail-open, see module docstring
        logger.exception("Rate limiter unavailable; allowing request")
        return
    if count > limit:
        retry_after = max(int(ttl), 1)
        logger.warning("Rate limit exceeded on %s", key.split(":")[0])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
