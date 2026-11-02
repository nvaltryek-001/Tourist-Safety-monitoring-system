"""Shared test setup.

Every API test runs against a throw-away SQLite file in a temp directory —
never against tourist_safety.db and never with real personal data. The
email addresses used here are fictitious.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_TMP = tempfile.mkdtemp(prefix="tsm_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-123456"
os.environ["OTP_DEV_ECHO"] = "true"
os.environ["SEED_DEMO_STAFF"] = "true"
os.environ["EMAIL_PROVIDER"] = "none"
os.environ["EXPO_PUSH_ENABLED"] = "false"
os.environ["ADMIN_ALERT_EMAIL"] = "alerts@example.invalid"
os.environ["AUTO_IMPORT_FACILITIES"] = "false"
# Test-only passwords for the seeded demo accounts (real installs get random ones).
os.environ["DEMO_SUPERADMIN_PASSWORD"] = "TestSuper12345"
os.environ["DEMO_ADMIN_PASSWORD"] = "TestAdmin12345"
os.environ["DEMO_POLICE_PASSWORD"] = "TestPolice12345"

ADMIN = ("admin@demo.local", "TestAdmin12345")
SUPER = ("superadmin@demo.local", "TestSuper12345")
POLICE = ("police@demo.local", "TestPolice12345")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.core import security
    from app.core.config import reset_settings_cache
    from app.core.ratelimit import limiter
    from app.database import Base, engine

    security.PBKDF2_ITERATIONS = 1000  # keep tests fast
    reset_settings_cache()
    limiter.reset()
    Base.metadata.drop_all(bind=engine)
    from app.main import app

    with TestClient(app) as c:
        yield c
    limiter.reset()


@pytest.fixture
def db_session(client):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def staff_headers(client, creds=ADMIN) -> dict:
    r = client.post("/api/v1/auth/staff/login", json={"email": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_tourist(client, code="T-TEST-01", gmail="test.tourist.one@gmail.com", consent=True, name="Test Tourist") -> dict:
    admin = staff_headers(client, ADMIN)
    r = client.post("/api/v1/admin/tourists", headers=admin, json={
        "tourist_code": code, "name": name, "login_gmail": gmail,
        "emergency_contact_name": "Test Contact", "emergency_contact_email": "contact@example.invalid",
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/tourist/request-otp", json={"email": gmail})
    assert r.status_code == 200, r.text
    otp = r.json()["dev_otp"]
    r = client.post("/api/v1/auth/tourist/verify-otp", json={"email": gmail, "code": otp})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if consent:
        assert client.post("/api/v1/me/consent", headers=headers, json={"granted": True}).status_code == 200
    return headers


@pytest.fixture
def admin_headers(client):
    return staff_headers(client, ADMIN)


@pytest.fixture
def police_headers(client):
    return staff_headers(client, POLICE)


@pytest.fixture
def tourist_headers(client):
    return make_tourist(client)


@pytest.fixture
def restricted_zone(client, admin_headers):
    r = client.post("/api/v1/zones", headers=admin_headers, json={
        "name": "Test Restricted Zone", "latitude": 13.0, "longitude": 77.0,
        "radius_meters": 100, "zone_type": "RESTRICTED",
    })
    assert r.status_code == 201, r.text
    return r.json()
