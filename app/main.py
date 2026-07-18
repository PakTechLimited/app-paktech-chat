import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.endpoints import admin, auth, health, messages, posts, rooms, websocket
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import Base, engine
from app.services.redis_service import close_redis

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PakTech Chat",
    description="Real-time WebSocket chat — FastAPI + Redis Pub/Sub + PostgreSQL",
    version="2.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(rooms.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(websocket.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Starting PakTech Chat v2 (env=%s)", settings.app_env)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialised")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_redis()
    await engine.dispose()
    logger.info("PakTech Chat shutdown complete")
