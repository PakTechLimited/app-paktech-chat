import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.dependencies import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.post import Post, PostComment, PostLike
from app.models.user import User

router = APIRouter(prefix="/posts", tags=["social wall"])
logger = logging.getLogger(__name__)


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    tag: str | None = Field(None, max_length=50)


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


@router.get("/")
async def list_posts(
    tag: str | None = Query(None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    q = (
        select(Post)
        .options(selectinload(Post.author))
        .order_by(desc(Post.created_at))
        .limit(limit)
    )
    if tag:
        q = q.where(Post.tag == tag)
    result = await db.execute(q)
    posts = result.scalars().all()

    liked_ids = set()
    if current_user:
        likes = await db.execute(
            select(PostLike.post_id).where(PostLike.user_id == current_user.id)
        )
        liked_ids = {r[0] for r in likes.all()}

    return [
        {
            "id": p.id,
            "content": p.content,
            "tag": p.tag,
            "likes_count": p.likes_count,
            "comments_count": p.comments_count,
            "created_at": p.created_at,
            "liked_by_me": p.id in liked_ids,
            "author": {
                "id": p.author.id,
                "username": p.author.username,
                "display_name": p.author.display_name,
                "avatar_color": p.author.avatar_color,
            },
        }
        for p in posts
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = Post(content=payload.content, tag=payload.tag, author_id=current_user.id)
    db.add(post)
    await db.flush()
    return {
        "id": post.id,
        "content": post.content,
        "tag": post.tag,
        "created_at": post.created_at,
    }


@router.post("/{post_id}/like", status_code=status.HTTP_200_OK)
async def toggle_like(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    like_result = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id, PostLike.user_id == current_user.id
        )
    )
    existing_like = like_result.scalar_one_or_none()

    if existing_like:
        await db.delete(existing_like)
        post.likes_count = max(0, post.likes_count - 1)
        return {"liked": False, "likes_count": post.likes_count}
    else:
        db.add(PostLike(post_id=post_id, user_id=current_user.id))
        post.likes_count += 1
        return {"liked": True, "likes_count": post.likes_count}


@router.get("/{post_id}/comments")
async def get_comments(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PostComment)
        .options(selectinload(PostComment.author))
        .where(PostComment.post_id == post_id)
        .order_by(PostComment.created_at)
    )
    comments = result.scalars().all()
    return [
        {
            "id": c.id,
            "content": c.content,
            "created_at": c.created_at,
            "author": {
                "id": c.author.id,
                "username": c.author.username,
                "display_name": c.author.display_name,
                "avatar_color": c.author.avatar_color,
            },
        }
        for c in comments
    ]


@router.post("/{post_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    comment = PostComment(
        post_id=post_id, author_id=current_user.id, content=payload.content
    )
    db.add(comment)
    post.comments_count += 1
    await db.flush()
    return {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at,
    }
