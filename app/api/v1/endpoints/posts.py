import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import get_current_user
from app.core.rate_limit import enforce
from app.db.session import get_db
from app.models.post import Post, PostComment, PostLike
from app.models.user import User, UserRole

router = APIRouter(prefix="/posts", tags=["social wall"])
logger = logging.getLogger(__name__)


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    tag: str | None = Field(None, max_length=50)

    @field_validator("tag", mode="before")
    @classmethod
    def normalise_tag(cls, v):
        """'#Dev Ops' -> 'dev-ops'; blank -> None."""
        if v is None:
            return None
        slug = re.sub(r"[^a-z0-9]+", "-", str(v).lower()).strip("-")
        return slug or None


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


def _author(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "avatar_color": u.avatar_color,
    }


def _post_out(p: Post, liked: bool = False) -> dict:
    return {
        "id": p.id,
        "content": p.content,
        "tag": p.tag,
        "likes_count": p.likes_count,
        "comments_count": p.comments_count,
        "created_at": p.created_at,
        "liked_by_me": liked,
        "author": _author(p.author),
    }


@router.get("/")
async def list_posts(
    tag: str | None = Query(None),
    before: int | None = Query(None, description="Return posts older than this id"),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Post).options(selectinload(Post.author))
    if tag:
        q = q.where(Post.tag == tag)
    if before:
        q = q.where(Post.id < before)
    q = q.order_by(desc(Post.id)).limit(limit)
    posts = (await db.execute(q)).scalars().all()

    likes = await db.execute(
        select(PostLike.post_id).where(PostLike.user_id == current_user.id)
    )
    liked_ids = {r[0] for r in likes.all()}
    return [_post_out(p, p.id in liked_ids) for p in posts]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await enforce(f"post:{current_user.id}", limit=10, window_seconds=60)
    post = Post(content=payload.content, tag=payload.tag, author_id=current_user.id)
    db.add(post)
    await db.flush()
    await db.refresh(post, ["author"])
    return _post_out(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = (
        await db.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    if post.author_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403, detail="You can only delete your own posts."
        )
    await db.delete(post)


@router.post("/{post_id}/like", status_code=status.HTTP_200_OK)
async def toggle_like(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await enforce(f"like:{current_user.id}", limit=60, window_seconds=60)
    # FOR UPDATE serialises concurrent toggles on the same post, so a double-click
    # can't insert two likes or lose a count update.
    post = (
        await db.execute(select(Post).where(Post.id == post_id).with_for_update())
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    existing_like = (
        await db.execute(
            select(PostLike).where(
                PostLike.post_id == post_id, PostLike.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()

    if existing_like:
        await db.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        return {"liked": False, "likes_count": post.likes_count}
    db.add(PostLike(post_id=post_id, user_id=current_user.id))
    post.likes_count += 1
    return {"liked": True, "likes_count": post.likes_count}


@router.get("/{post_id}/comments")
async def get_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PostComment)
        .options(selectinload(PostComment.author))
        .where(PostComment.post_id == post_id)
        .order_by(PostComment.created_at, PostComment.id)
    )
    return [
        {
            "id": c.id,
            "content": c.content,
            "created_at": c.created_at,
            "author": _author(c.author),
        }
        for c in result.scalars().all()
    ]


@router.post("/{post_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await enforce(f"comment:{current_user.id}", limit=30, window_seconds=60)
    post = (
        await db.execute(select(Post).where(Post.id == post_id).with_for_update())
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    comment = PostComment(
        post_id=post_id, author_id=current_user.id, content=payload.content
    )
    db.add(comment)
    post.comments_count += 1
    await db.flush()
    await db.refresh(comment)
    return {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at,
        "author": _author(current_user),
    }
