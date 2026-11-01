"""Smoke test against a *running* server (skipped when none is reachable).

Run: SMART_TOURIST_API_URL=https://your-api.onrender.com pytest tests/test_health_api.py
"""
import os

import pytest

API_BASE_URL = os.getenv("SMART_TOURIST_API_URL", "http://127.0.0.1:8000")


def test_live_health_endpoint():
    httpx = pytest.importorskip("httpx")
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=3.0)
    except httpx.HTTPError:
        pytest.skip(f"no server reachable at {API_BASE_URL}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
