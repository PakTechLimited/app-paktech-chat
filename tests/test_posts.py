"""Social wall: auth, likes, comments, delete permissions, cascade, limits."""

import asyncio

from sqlalchemy import update

from app.db import session as db_session
from app.models.user import User, UserRole

ALICE = {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"}
BOB = {"username": "bob", "email": "bob@example.com", "password": "s3cret-pass!"}


def _login(client, creds):
    r = client.post("/api/v1/auth/register", json=creds)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post(client, h, content="hello wall", tag=None):
    r = client.post("/api/v1/posts/", json={"content": content, "tag": tag}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_wall_requires_login(auth_client):
    assert auth_client.get("/api/v1/posts/").status_code == 401
    assert auth_client.post("/api/v1/posts/", json={"content": "x"}).status_code == 401
    assert auth_client.get("/api/v1/posts/1/comments").status_code == 401


def test_create_returns_full_post_with_normalised_tag(auth_client):
    h = _login(auth_client, ALICE)
    p = _post(auth_client, h, "Kubernetes tips", tag="#Dev Ops")
    assert p["tag"] == "dev-ops"
    assert p["author"]["username"] == "alice"
    assert p["likes_count"] == 0 and p["liked_by_me"] is False
    assert _post(auth_client, h, "no tag", tag="   ")["tag"] is None


def test_like_toggles_and_is_per_user(auth_client):
    a, b = _login(auth_client, ALICE), _login(auth_client, BOB)
    pid = _post(auth_client, a)["id"]

    r = auth_client.post(f"/api/v1/posts/{pid}/like", headers=b).json()
    assert r == {"liked": True, "likes_count": 1}
    r = auth_client.post(f"/api/v1/posts/{pid}/like", headers=a).json()
    assert r["likes_count"] == 2

    feed_b = auth_client.get("/api/v1/posts/", headers=b).json()
    assert feed_b[0]["liked_by_me"] is True and feed_b[0]["likes_count"] == 2

    r = auth_client.post(f"/api/v1/posts/{pid}/like", headers=b).json()
    assert r == {"liked": False, "likes_count": 1}


def test_comments_add_list_and_count(auth_client):
    a, b = _login(auth_client, ALICE), _login(auth_client, BOB)
    pid = _post(auth_client, a)["id"]
    c = auth_client.post(
        f"/api/v1/posts/{pid}/comments", json={"content": "nice"}, headers=b
    )
    assert c.status_code == 201 and c.json()["author"]["username"] == "bob"
    listed = auth_client.get(f"/api/v1/posts/{pid}/comments", headers=a).json()
    assert [x["content"] for x in listed] == ["nice"]
    assert auth_client.get("/api/v1/posts/", headers=a).json()[0]["comments_count"] == 1
    missing = auth_client.post(
        "/api/v1/posts/999/comments", json={"content": "x"}, headers=a
    )
    assert missing.status_code == 404


def test_pagination_with_before_cursor(auth_client):
    h = _login(auth_client, ALICE)
    ids = [_post(auth_client, h, f"post {i}")["id"] for i in range(5)]
    page1 = auth_client.get("/api/v1/posts/?limit=2", headers=h).json()
    assert [p["id"] for p in page1] == [ids[4], ids[3]]
    page2 = auth_client.get(
        f"/api/v1/posts/?limit=2&before={page1[-1]['id']}", headers=h
    ).json()
    assert [p["id"] for p in page2] == [ids[2], ids[1]]


def test_only_author_or_admin_can_delete(auth_client):
    a, b = _login(auth_client, ALICE), _login(auth_client, BOB)
    pid = _post(auth_client, a)["id"]
    assert auth_client.delete(f"/api/v1/posts/{pid}", headers=b).status_code == 403
    assert auth_client.delete(f"/api/v1/posts/{pid}", headers=a).status_code == 204
    assert auth_client.get("/api/v1/posts/", headers=a).json() == []
    assert auth_client.delete(f"/api/v1/posts/{pid}", headers=a).status_code == 404


def test_admin_can_delete_post_that_has_likes_and_comments(auth_client):
    """Regression: deleting a post with children used to crash with an FK error."""
    a, b = _login(auth_client, ALICE), _login(auth_client, BOB)
    pid = _post(auth_client, a)["id"]
    auth_client.post(f"/api/v1/posts/{pid}/like", headers=b)
    auth_client.post(f"/api/v1/posts/{pid}/comments", json={"content": "c"}, headers=b)

    async def _promote():
        async with db_session.AsyncSessionLocal() as db:
            await db.execute(
                update(User).where(User.username == "bob").values(role=UserRole.admin)
            )
            await db.commit()

    asyncio.run(_promote())
    r = auth_client.delete(f"/api/v1/admin/posts/{pid}", headers=b)
    assert r.status_code == 204, r.text
    assert auth_client.get("/api/v1/posts/", headers=a).json() == []


def test_post_creation_is_rate_limited(auth_client):
    h = _login(auth_client, ALICE)
    codes = [
        auth_client.post(
            "/api/v1/posts/", json={"content": f"spam {i}"}, headers=h
        ).status_code
        for i in range(11)
    ]
    assert codes[:10] == [201] * 10 and codes[10] == 429
