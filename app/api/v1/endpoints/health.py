import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.session import engine
from app.services.redis_service import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["health"])
async def health_check() -> JSONResponse:
    """Liveness + readiness probe endpoint for Kubernetes."""
    checks: dict[str, str] = {}

    # PostgreSQL check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        logger.error("Postgres health check failed: %s", exc)
        checks["postgres"] = "error"

    # Redis check
    try:
        client = await get_redis()
        await client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        checks["redis"] = "error"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    http_status = 200 if status == "healthy" else 503

    return JSONResponse(
        content={"status": status, "checks": checks},
        status_code=http_status,
    )
