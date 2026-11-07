"""Alembic migrations: fresh install, upgrade of legacy databases, no drift."""

import pytest
import sqlalchemy as sa

import app.models  # noqa: F401
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.db.session import Base


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "mig.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{path}")
    engine = sa.create_engine(f"sqlite:///{path}")
    yield cfg, engine
    engine.dispose()


def _version(engine) -> str:
    with engine.connect() as c:
        return c.execute(
            sa.text("select version_num from alembic_version")
        ).scalar_one()


def test_fresh_database_gets_every_table_and_the_like_constraint(db):
    cfg, engine = db
    command.upgrade(cfg, "head")
    insp = sa.inspect(engine)
    assert set(Base.metadata.tables) <= set(insp.get_table_names())
    names = {c["name"] for c in insp.get_unique_constraints("post_likes")}
    assert "uq_post_likes_post_user" in names
    assert _version(engine) == "0002"


def test_migrated_schema_matches_the_models(db):
    cfg, engine = db
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_existing_create_all_database_upgrades_cleanly(db):
    """Databases built by the old startup hook need no manual `alembic stamp`."""
    cfg, engine = db
    Base.metadata.create_all(engine)
    command.upgrade(cfg, "head")
    assert _version(engine) == "0002"


def test_duplicate_likes_are_cleaned_before_the_constraint(db):
    cfg, engine = db
    command.upgrade(cfg, "0001")
    with engine.begin() as c:
        c.execute(
            sa.text(
                "insert into users (id, username, email, hashed_password, role, "
                "is_active, is_verified) values "
                "(1,'a','a@x.io','h','member',1,0), (2,'b','b@x.io','h','member',1,0)"
            )
        )
        c.execute(
            sa.text(
                "insert into posts (id, content, author_id, likes_count, comments_count)"
                " values (1, 'hi', 1, 4, 0)"
            )
        )
        # user 1 liked three times (a race), user 2 once
        c.execute(
            sa.text(
                "insert into post_likes (post_id, user_id) "
                "values (1,1),(1,1),(1,1),(1,2)"
            )
        )
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        likes = c.execute(sa.text("select user_id from post_likes order by id")).all()
        count = c.execute(
            sa.text("select likes_count from posts where id=1")
        ).scalar_one()
    assert [r[0] for r in likes] == [1, 2]
    assert count == 2
    with engine.begin() as c, pytest.raises(sa.exc.IntegrityError):
        c.execute(sa.text("insert into post_likes (post_id, user_id) values (1,2)"))


def test_downgrade_to_base_removes_everything(db):
    cfg, engine = db
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert set(sa.inspect(engine).get_table_names()) <= {"alembic_version"}
