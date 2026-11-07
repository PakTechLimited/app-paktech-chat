"""Baseline schema (what create_all used to build).

Tables that already exist are left alone, so a database created by the old
``create_all`` startup hook upgrades cleanly without a manual ``alembic stamp``.

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOW = sa.func.now()


def _ts(name: str, **kw) -> sa.Column:
    kw.setdefault("nullable", False)
    return sa.Column(name, sa.DateTime(timezone=True), **kw)


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(50), nullable=False),
            sa.Column("email", sa.String(255), nullable=False),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=True),
            sa.Column("avatar_color", sa.String(20), nullable=True),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("role", sa.String(6), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("is_verified", sa.Boolean(), nullable=False),
            _ts("created_at", server_default=NOW),
            _ts("last_seen", nullable=True),
        )
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "rooms" not in existing:
        op.create_table(
            "rooms",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            _ts("created_at", server_default=NOW),
        )
        op.create_index("ix_rooms_id", "rooms", ["id"])
        op.create_index("ix_rooms_name", "rooms", ["name"], unique=True)

    if "messages" not in existing:
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False
            ),
            sa.Column(
                "author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            _ts("created_at", server_default=NOW),
        )
        op.create_index("ix_messages_id", "messages", ["id"])
        op.create_index("ix_messages_room_id", "messages", ["room_id"])
        op.create_index("ix_messages_author_id", "messages", ["author_id"])
        op.create_index("ix_messages_created_at", "messages", ["created_at"])

    if "posts" not in existing:
        op.create_table(
            "posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("tag", sa.String(50), nullable=True),
            sa.Column(
                "author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("likes_count", sa.Integer(), nullable=False),
            sa.Column("comments_count", sa.Integer(), nullable=False),
            _ts("created_at", server_default=NOW),
        )
        op.create_index("ix_posts_id", "posts", ["id"])
        op.create_index("ix_posts_tag", "posts", ["tag"])
        op.create_index("ix_posts_author_id", "posts", ["author_id"])
        op.create_index("ix_posts_created_at", "posts", ["created_at"])

    if "post_likes" not in existing:
        op.create_table(
            "post_likes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False
            ),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            _ts("created_at", server_default=NOW),
        )
        op.create_index("ix_post_likes_id", "post_likes", ["id"])
        op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])
        op.create_index("ix_post_likes_user_id", "post_likes", ["user_id"])

    if "post_comments" not in existing:
        op.create_table(
            "post_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False
            ),
            sa.Column(
                "author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("content", sa.Text(), nullable=False),
            _ts("created_at", server_default=NOW),
        )
        op.create_index("ix_post_comments_id", "post_comments", ["id"])
        op.create_index("ix_post_comments_post_id", "post_comments", ["post_id"])
        op.create_index("ix_post_comments_author_id", "post_comments", ["author_id"])


def downgrade() -> None:
    for table in (
        "post_comments",
        "post_likes",
        "posts",
        "messages",
        "rooms",
        "users",
    ):
        op.drop_table(table)
