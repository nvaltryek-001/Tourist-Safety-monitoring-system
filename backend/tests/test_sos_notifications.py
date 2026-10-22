import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sos_client(monkeypatch):
    monkeypatch.setenv("SOS_EMAIL_ENABLED", "false")
    monkeypatch.setenv("SOS_SMS_ENABLED", "false")
    monkeypatch.setenv("SOS_VOICE_ENABLED", "false")

    from app.main import app
    from app.database import Base, engine as app_engine, get_db

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, TestSession
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_sos_records_alert_and_uses_dry_run(sos_client):
    client, TestSession = sos_client

    from app.models.models import Tourist, SOSAlert

    db = TestSession()
    try:
        db.add(Tourist(
            tourist_code="SOS-TEST-001",
            name="Test Tourist",
            emergency_contact_name="Test Contact",
            emergency_contact_email="contact@example.invalid",
            emergency_contact_phone="+15550000001",
            latitude=12.0,
            longitude=77.0,
        ))
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/tourists/SOS-TEST-001/sos",
        json={"message": "Automated test only"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "SOS alert recorded"
    assert body["tourist_code"] == "SOS-TEST-001"
    assert body["latitude"] == 12.0
    assert body["longitude"] == 77.0

    statuses = {
        (item["channel"], item["recipient_type"]): item["status"]
        for item in body["notification_results"]
    }
    assert statuses[("email", "emergency_contact")] == "dry_run"
    assert statuses[("email", "admin")] == "dry_run"
    assert statuses[("sms", "emergency_contact")] == "dry_run"
    assert statuses[("voice", "emergency_contact")] == "dry_run"

    db = TestSession()
    try:
        alert = db.query(SOSAlert).filter_by(
            tourist_code="SOS-TEST-001"
        ).first()
        tourist = db.query(Tourist).filter_by(
            tourist_code="SOS-TEST-001"
        ).first()

        assert alert is not None
        assert alert.message == "Automated test only"
        assert tourist.safety_status == "SOS"
    finally:
        db.close()


def test_sos_unknown_tourist_returns_404(sos_client):
    client, _ = sos_client

    response = client.post(
        "/tourists/DOES-NOT-EXIST/sos",
        json={"message": "Automated test only"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Tourist not found"
