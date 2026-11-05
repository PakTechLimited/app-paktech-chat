import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.core.csrf import require_csrf
from app.core.rate_limit import client_ip, enforce
from app.core.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    pick_avatar_color,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services.token_store import consume_refresh, revoke_all, store_refresh

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

REFRESH_COOKIE = "pt_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"  # browser only sends it to auth endpoints


async def _start_session(response: Response, user: User) -> TokenResponse:
    """Issue a rotated refresh token as an httpOnly cookie + a fresh access token."""
    refresh_token, jti = create_refresh_token(user.id)
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    await store_refresh(jti, user.id, ttl)
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=ttl,
        httponly=True,  # not readable by JS -> XSS cannot steal it
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_color=user.avatar_color or "#7c5cbf",
        role=user.role.value,
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await enforce(f"register:{client_ip(request)}", limit=5, window_seconds=3600)
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered.",
        )
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        avatar_color=pick_avatar_color(payload.username),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("New user registered: %s", user.username)
    return await _start_session(response, user)


@router.post(
    "/login", response_model=TokenResponse, dependencies=[Depends(require_csrf)]
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Per-IP cap stops one host hammering; per-account cap stops a distributed
    # attack on a single email.
    await enforce(f"login-ip:{client_ip(request)}", limit=20, window_seconds=300)
    await enforce(f"login-acct:{payload.email.lower()}", limit=5, window_seconds=300)
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return await _start_session(response, user)


@router.post(
    "/refresh", response_model=TokenResponse, dependencies=[Depends(require_csrf)]
)
async def refresh(
    request: Request,
    response: Response,
    pt_refresh: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    await enforce(f"refresh:{client_ip(request)}", limit=60, window_seconds=60)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )
    claims = decode_token(pt_refresh) if pt_refresh else None
    if not claims or claims.get("type") != "refresh" or not claims.get("jti"):
        _clear_cookie(response)
        raise invalid
    user_id = await consume_refresh(claims["jti"])
    if user_id is None or user_id != int(claims["sub"]):
        # Valid signature but not live: already used or revoked -> possible replay.
        await revoke_all(int(claims["sub"]))
        logger.warning(
            "Session replay detected; all sessions revoked for user %s", claims["sub"]
        )
        _clear_cookie(response)
        raise invalid
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        _clear_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return await _start_session(response, user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def logout(response: Response, pt_refresh: str | None = Cookie(default=None)):
    claims = decode_token(pt_refresh) if pt_refresh else None
    if claims and claims.get("jti"):
        await consume_refresh(claims["jti"])
    _clear_cookie(response)


@router.get("/me", response_model=UserMeResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user
