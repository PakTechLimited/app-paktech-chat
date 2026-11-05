"""Server-side allow-list of live refresh tokens (Redis).

Every refresh token carries a unique ``jti``. Only tokens whose jti is present
in Redis are valid. Using one *consumes* it (atomic GETDEL), so a token works
exactly once: the endpoint then issues a fresh one (rotation). If a consumed or
unknown jti is presented again (token theft / replay), the caller revokes every
session for that user.
"""

from app.services.redis_service import get_redis

_TOKEN_KEY = "refresh:{jti}"
_USER_KEY = "user_refresh:{user_id}"


async def store_refresh(jti: str, user_id: int, ttl_seconds: int) -> None:
    r = await get_redis()
    await r.set(_TOKEN_KEY.format(jti=jti), str(user_id), ex=ttl_seconds)
    await r.sadd(_USER_KEY.format(user_id=user_id), jti)
    await r.expire(_USER_KEY.format(user_id=user_id), ttl_seconds)


async def consume_refresh(jti: str) -> int | None:
    """Atomically delete the jti. Returns its user id, or None if not live."""
    r = await get_redis()
    value = await r.getdel(_TOKEN_KEY.format(jti=jti))
    if value is None:
        return None
    user_id = int(value)
    await r.srem(_USER_KEY.format(user_id=user_id), jti)
    return user_id


async def revoke_all(user_id: int) -> None:
    """Invalidate every refresh token a user holds (logout-everywhere)."""
    r = await get_redis()
    key = _USER_KEY.format(user_id=user_id)
    jtis = await r.smembers(key)
    if jtis:
        await r.delete(*[_TOKEN_KEY.format(jti=j) for j in jtis])
    await r.delete(key)
