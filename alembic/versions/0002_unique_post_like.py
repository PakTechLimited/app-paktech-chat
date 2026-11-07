"""One like per (post, user): unique constraint.

Duplicates could only exist from a like/unlike race before the row lock was
added; remove them (keeping the oldest) and recompute the cached counters
before the constraint goes on.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = "uq_post_likes_post_user"


def upgrade() -> None:
    bind = op.get_bind()
    existing = {
        c["name"] for c in sa.inspect(bind).get_unique_constraints("post_likes")
    }
    if CONSTRAINT in existing:
        return  # fresh create_all databases already have it

    op.execute(
        """
        DELETE FROM post_likes WHERE id NOT IN (
            SELECT MIN(id) FROM post_likes GROUP BY post_id, user_id
        )
        """
    )
    op.execute(
        """
        UPDATE posts SET likes_count = (
            SELECT COUNT(*) FROM post_likes WHERE post_likes.post_id = posts.id
        )
        """
    )
    with op.batch_alter_table("post_likes") as batch:
        batch.create_unique_constraint(CONSTRAINT, ["post_id", "user_id"])


def downgrade() -> None:
    with op.batch_alter_table("post_likes") as batch:
        batch.drop_constraint(CONSTRAINT, type_="unique")
