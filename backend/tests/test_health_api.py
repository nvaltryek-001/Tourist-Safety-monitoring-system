import os

import httpx
import pytest


API_BASE_URL = os.getenv("SMART_TOURIST_API_URL", "http://127.0.0.1:8000")


@pytest.fixture
def api_client():
    with httpx.Client(base_url=API_BASE_URL, timeout=5.0) as client:
        yield client


def test_health_endpoint_returns_healthy_status(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "smart-tourist-management"
    assert body["timestamp"]
