"""Rooms and message history over REST."""

import pytest

from tests.helpers import register


def test_rooms_require_login(auth_client):
    assert auth_client.get("/api/v1/rooms/").status_code == 401
    assert auth_client.post("/api/v1/rooms/", json={"name": "x"}).status_code == 401
    assert auth_client.get("/api/v1/rooms/1").status_code == 401


def test_rooms_list_is_sorted_and_includes_the_seed_rooms(auth_client):
    h = register(auth_client, "alice")
    names = [r["name"] for r in auth_client.get("/api/v1/rooms/", headers=h).json()]
    assert names == ["engineering", "general", "random"]


def test_create_get_and_duplicate_room(auth_client):
    h = register(auth_client, "alice")
    r = auth_client.post(
        "/api/v1/rooms/", json={"name": "ops", "description": "On call"}, headers=h
    )
    assert r.status_code == 201
    room = r.json()
    assert room["name"] == "ops" and room["description"] == "On call"
    assert auth_client.get(f"/api/v1/rooms/{room['id']}", headers=h).json() == room
    dup = auth_client.post("/api/v1/rooms/", json={"name": "ops"}, headers=h)
    assert dup.status_code == 409


@pytest.mark.parametrize(
    "body",
    [{"name": ""}, {"name": "x" * 101}, {"name": "ok", "description": "d" * 256}],
)
def test_room_validation(auth_client, body):
    h = register(auth_client, "alice")
    assert auth_client.post("/api/v1/rooms/", json=body, headers=h).status_code == 422


def test_unknown_room_is_404(auth_client):
    h = register(auth_client, "alice")
    assert auth_client.get("/api/v1/rooms/999", headers=h).status_code == 404


def test_room_creation_is_rate_limited(auth_client):
    h = register(auth_client, "alice")
    codes = [
        auth_client.post(
            "/api/v1/rooms/", json={"name": f"r{i}"}, headers=h
        ).status_code
        for i in range(6)
    ]
    assert codes == [201] * 5 + [429]


def test_messages_require_login(auth_client):
    assert auth_client.get("/api/v1/messages/1").status_code == 401
    body = {"content": "x", "room_id": 1}
    assert auth_client.post("/api/v1/messages/", json=body).status_code == 401


def test_post_then_read_history_oldest_first(auth_client):
    a, b = register(auth_client, "alice"), register(auth_client, "bob")
    for h, text in [(a, "first"), (b, "second"), (a, "third")]:
        r = auth_client.post(
            "/api/v1/messages/", json={"content": text, "room_id": 1}, headers=h
        )
        assert r.status_code == 201
    history = auth_client.get("/api/v1/messages/1", headers=a).json()
    assert [m["content"] for m in history] == ["first", "second", "third"]
    assert [m["author_username"] for m in history] == ["alice", "bob", "alice"]


def test_history_limit_returns_the_latest_messages(auth_client):
    h = register(auth_client, "alice")
    for i in range(5):
        auth_client.post(
            "/api/v1/messages/", json={"content": f"m{i}", "room_id": 1}, headers=h
        )
    r = auth_client.get("/api/v1/messages/1?limit=2", headers=h).json()
    assert [m["content"] for m in r] == ["m3", "m4"]


@pytest.mark.parametrize("limit", [0, 201, -1])
def test_history_limit_is_validated(auth_client, limit):
    h = register(auth_client, "alice")
    r = auth_client.get(f"/api/v1/messages/1?limit={limit}", headers=h)
    assert r.status_code == 422


def test_history_is_per_room(auth_client):
    h = register(auth_client, "alice")
    auth_client.post(
        "/api/v1/messages/", json={"content": "a", "room_id": 1}, headers=h
    )
    assert auth_client.get("/api/v1/messages/2", headers=h).json() == []


def test_posting_validates_room_and_content(auth_client):
    h = register(auth_client, "alice")
    r = auth_client.post(
        "/api/v1/messages/", json={"content": "x", "room_id": 999}, headers=h
    )
    assert r.status_code == 404
    for content in ("", "x" * 4001):
        r = auth_client.post(
            "/api/v1/messages/", json={"content": content, "room_id": 1}, headers=h
        )
        assert r.status_code == 422
