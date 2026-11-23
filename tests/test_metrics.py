"""Tests for the Prometheus /metrics endpoint and request metrics."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with (
        patch("app.db.session.engine") as mock_engine,
        patch("app.services.redis_service.get_redis") as mock_redis,
        patch("app.main.seed_default_rooms", new=AsyncMock()),
    ):
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_engine.connect.return_value = mock_conn
        mock_engine.dispose = AsyncMock()

        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_redis_client

        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_metrics_endpoint_returns_prometheus_text(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "ws_connections_active" in resp.text
    assert "ws_messages_total" in resp.text


def test_requests_are_counted_by_route_template(client):
    client.get("/api/v1/health")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",route="/api/v1/health",status=' in body
    assert "http_request_duration_seconds_bucket" in body


def test_unknown_paths_do_not_create_label_per_url(client):
    client.get("/definitely/not/a/route/12345")
    body = client.get("/metrics").text
    assert 'route="unmatched"' in body
    assert "/definitely/not/a/route" not in body


def test_metrics_endpoint_does_not_count_itself(client):
    client.get("/metrics")
    body = client.get("/metrics").text
    assert 'route="/metrics"' not in body


def test_metrics_endpoint_is_not_in_openapi(client):
    # include_in_schema=False keeps it out of the generated API docs
    from app.main import app

    assert "/metrics" not in app.openapi()["paths"]


def test_path_parameters_do_not_create_label_per_value(client):
    client.get("/api/v1/rooms/987654")
    body = client.get("/metrics").text
    assert "987654" not in body
