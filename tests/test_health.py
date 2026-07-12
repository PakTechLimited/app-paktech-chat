"""
Smoke tests for the health endpoint.
Full integration tests require a running Postgres + Redis (use docker-compose).
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with (
        patch("app.db.session.engine") as mock_engine,
        patch("app.services.redis_service.get_redis") as mock_redis,
    ):

        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value = mock_conn

        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_redis_client

        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health_endpoint_exists(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "postgres" in data["checks"]
    assert "redis" in data["checks"]
