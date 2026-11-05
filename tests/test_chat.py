"""Chat: authenticated WebSocket, persisted messages, locked-down REST."""

import asyncio

import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.db import session as db_session
from app.models.message import Message

pytestmark = pytest.mark.timeout(20)

ALICE = {"username": "alice", "email": "alice@example.com", "password": "s3cret-pass!"}
BOB = {"username": "bob", "email": "bob@example.com", "password": "s3cret-pass!"}
ENGINEERING = 2  # seeded as the 2nd default room


def _token(client, creds):
    r = client.post("/api/v1/auth/register", json=creds)
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _open(client, token, room=ENGINEERING):
    ws = client.websocket_connect(f"/ws/{room}")
    sock = ws.__enter__()
    sock.send_json({"type": "auth", "token": token})
    return ws, sock


def _until(sock, kind):
    for _ in range(100):
        event = sock.receive_json()
        if event["type"] == kind:
            return event
    raise AssertionError(f"never received {kind}")


def _close_code(sock):
    with pytest.raises(WebSocketDisconnect) as exc:
        sock.receive_json()
    return exc.value.code


def test_stranger_without_auth_frame_is_rejected(auth_client):
    with auth_client.websocket_connect(f"/ws/{ENGINEERING}") as sock:
        sock.send_json({"type": "message", "content": "hi"})  # not an auth frame
        assert _close_code(sock) == 4401


def test_forged_token_is_rejected(auth_client):
    with auth_client.websocket_connect(f"/ws/{ENGINEERING}") as sock:
        sock.send_json({"type": "auth", "token": "not-a-jwt"})
        assert _close_code(sock) == 4401


def test_refresh_token_cannot_authenticate_socket(auth_client):
    _token(auth_client, ALICE)
    refresh = auth_client.cookies.get("pt_refresh", path="/api/v1/auth")
    with auth_client.websocket_connect(f"/ws/{ENGINEERING}") as sock:
        sock.send_json({"type": "auth", "token": refresh})
        assert _close_code(sock) == 4401


def test_unknown_room_is_rejected(auth_client):
    token = _token(auth_client, ALICE)
    with auth_client.websocket_connect("/ws/999") as sock:
        sock.send_json({"type": "auth", "token": token})
        assert _close_code(sock) == 4404


def test_foreign_origin_is_rejected(auth_client):
    with pytest.raises(WebSocketDisconnect):
        with auth_client.websocket_connect(
            f"/ws/{ENGINEERING}", headers={"origin": "http://evil.example"}
        ) as sock:
            sock.receive_json()


def test_message_is_attributed_to_account_and_persisted(auth_client):
    token = _token(auth_client, ALICE)
    ws, sock = _open(auth_client, token)
    try:
        assert _until(sock, "ready")["username"] == "alice"
        # A client-supplied username must be ignored.
        sock.send_json({"type": "message", "content": "hello", "username": "bob"})
        event = _until(sock, "message")
    finally:
        ws.__exit__(None, None, None)
    assert event["username"] == "alice" and event["content"] == "hello"
    assert event["id"] > 0

    async def _rows():
        async with db_session.AsyncSessionLocal() as db:
            return (await db.execute(select(Message))).scalars().all()

    rows = asyncio.run(_rows())
    assert [(m.content, m.room_id) for m in rows] == [("hello", ENGINEERING)]


def test_second_tab_does_not_break_the_first(auth_client):
    token = _token(auth_client, ALICE)
    ws1, tab1 = _open(auth_client, token)
    _until(tab1, "ready")
    ws2, tab2 = _open(auth_client, token)
    _until(tab2, "ready")
    try:
        tab2.send_json({"type": "message", "content": "from tab two"})
        assert _until(tab1, "message")["content"] == "from tab two"
        assert _until(tab2, "message")["content"] == "from tab two"
    finally:
        ws2.__exit__(None, None, None)
    # Tab 1 still works after tab 2 closed.
    try:
        tab1.send_json({"type": "message", "content": "still here"})
        assert _until(tab1, "message")["content"] == "still here"
    finally:
        ws1.__exit__(None, None, None)


def test_overlong_message_is_refused(auth_client):
    token = _token(auth_client, ALICE)
    ws, sock = _open(auth_client, token)
    try:
        _until(sock, "ready")
        sock.send_json({"type": "message", "content": "x" * 4001})
        assert "too long" in _until(sock, "error")["content"].lower()
    finally:
        ws.__exit__(None, None, None)


def test_message_flood_is_throttled(auth_client):
    token = _token(auth_client, ALICE)
    ws, sock = _open(auth_client, token)
    try:
        _until(sock, "ready")
        for i in range(31):
            sock.send_json({"type": "message", "content": f"m{i}"})
        assert "too fast" in _until(sock, "error")["content"].lower()
    finally:
        ws.__exit__(None, None, None)


def test_rest_endpoints_require_login(auth_client):
    assert auth_client.get("/api/v1/rooms/").status_code == 401
    assert auth_client.get(f"/api/v1/messages/{ENGINEERING}").status_code == 401
    r = auth_client.post(
        "/api/v1/messages/", json={"content": "x", "room_id": ENGINEERING}
    )
    assert r.status_code == 401


def test_rest_post_uses_token_user_not_query_author(auth_client):
    token = _token(auth_client, BOB)
    h = {"Authorization": f"Bearer {token}"}
    r = auth_client.post(
        "/api/v1/messages/?author_id=1",  # old spoofing vector: must be ignored
        json={"content": "hi", "room_id": ENGINEERING},
        headers=h,
    )
    assert r.status_code == 201 and r.json()["author_username"] == "bob"
    rooms = auth_client.get("/api/v1/rooms/", headers=h).json()
    assert [x["name"] for x in rooms] == ["engineering", "general", "random"]
