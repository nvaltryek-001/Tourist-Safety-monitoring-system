import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="module")
def app_client():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory(prefix="tourist_api_test_") as temp_dir:
        os.chdir(temp_dir)

        app = None
        get_db = None
        Base = None
        app_engine = None
        test_engine = None

        try:
            # Import only after switching to the isolated temporary directory.
            from app.main import app as imported_app
            from app.database import (
                Base as imported_base,
                engine as imported_app_engine,
                get_db as imported_get_db,
            )

            app = imported_app
            Base = imported_base
            app_engine = imported_app_engine
            get_db = imported_get_db

            test_engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )

            TestSessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=test_engine,
            )
            Base.metadata.create_all(bind=test_engine)

            def override_get_db():
                db = TestSessionLocal()
                try:
                    yield db
                finally:
                    db.close()

            app.dependency_overrides[get_db] = override_get_db

            with TestClient(app) as client:
                yield client

        finally:
            if app is not None and get_db is not None:
                app.dependency_overrides.pop(get_db, None)

            if test_engine is not None:
                if Base is not None:
                    Base.metadata.drop_all(bind=test_engine)
                test_engine.dispose()

            if app_engine is not None:
                app_engine.dispose()

            os.chdir(original_cwd)

def test_register_tourist_returns_registered_tourist(app_client):
    response = app_client.post(
        "/tourists",
        json={
            "tourist_code": "TEST-TOURIST-001",
            "name": "Test Tourist",
            "phone": "9000000001",
            "enrollment_number": "TEST-ENROLL-001",
            "college_email": "test-tourist-001@example.invalid",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Tourist registered"
    assert body["tourist"]["tourist_code"] == "TEST-TOURIST-001"
    assert body["tourist"]["name"] == "Test Tourist"
    assert body["tourist"]["safety_status"] == "SAFE"


def test_duplicate_tourist_code_returns_conflict(app_client):
    payload = {
        "tourist_code": "TEST-TOURIST-DUPLICATE",
        "name": "Duplicate Test",
    }

    first = app_client.post("/tourists", json=payload)
    second = app_client.post("/tourists", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Tourist code already exists"
