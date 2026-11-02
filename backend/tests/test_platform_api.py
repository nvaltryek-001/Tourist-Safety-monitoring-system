"""Notifications, WebSocket, migrations, audit logs and legacy contracts."""

import sqlite3

from conftest import ADMIN, staff_headers


def test_notification_provider_failure_is_recorded(client, tourist_headers, admin_headers, monkeypatch):
    from app.core.config import reset_settings_cache
    from app.services import notifications

    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("EMAIL_API_KEY", "test-key")
    monkeypatch.setenv("EMAIL_FROM", "alerts@example.invalid")
    reset_settings_cache()
    calls = []

    def failing(*args):
        calls.append(args)
        raise notifications.ProviderError("simulated outage")

    monkeypatch.setattr(notifications, "PROVIDERS", {"email": failing, "push": failing})
    monkeypatch.setattr(notifications.time, "sleep", lambda s: None)
    try:
        r = client.post("/api/v1/me/sos", headers=tourist_headers, json={"message": "test"})
        assert r.status_code == 200  # SOS is recorded even when every provider fails
        statuses = {(n["channel"], n.get("recipient_type")): n["status"] for n in r.json()["notification_results"]}
        assert statuses[("email", "admin")] == "FAILED"
        assert len(calls) == 2 * notifications.MAX_ATTEMPTS
        log = client.get("/api/v1/notifications/delivery-log?channel=EMAIL", headers=admin_headers).json()
        assert all(item["status"] == "FAILED" and item["attempts"] == 3 for item in log["items"])
    finally:
        monkeypatch.undo()
        reset_settings_cache()


def test_notification_provider_success_is_not_called_delivered(client, tourist_headers, monkeypatch):
    from app.core.config import reset_settings_cache
    from app.services import notifications

    monkeypatch.setenv("EXPO_PUSH_ENABLED", "true")
    reset_settings_cache()
    monkeypatch.setattr(notifications, "PROVIDERS", {"email": lambda *a: None, "push": lambda *a: None})
    try:
        client.patch("/api/v1/me", headers=tourist_headers, json={"expo_push_token": "ExponentPushToken[x]"})
        results = client.post("/api/v1/me/sos", headers=tourist_headers, json={}).json()["notification_results"]
        assert {"channel": "push", "status": "ACCEPTED_BY_PROVIDER"} in results
    finally:
        monkeypatch.undo()
        reset_settings_cache()


def test_websocket_receives_sos_event(client, tourist_headers):
    token = staff_headers(client, ADMIN)["Authorization"].split()[1]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json()["type"] == "hello"
        client.post("/api/v1/me/sos", headers=tourist_headers, json={"message": "ws test"})
        event = ws.receive_json()
        assert event["type"] == "sos.created" and event["data"]["tourist_code"] == "T-TEST-01"


def test_websocket_rejects_bad_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=nope") as ws:
            ws.receive_json()


def test_audit_log_records_logins(client, admin_headers):
    logs = client.get("/api/v1/admin/audit-logs?action=STAFF_LOGIN", headers=admin_headers).json()
    assert logs["total"] >= 1


def test_migration_upgrades_v1_database_without_losing_rows(tmp_path):
    """Build a database with the ORIGINAL v1 schema, then upgrade it."""
    from sqlalchemy import create_engine, inspect

    from app.migrations import restore_sqlite, run_migrations

    path = tmp_path / "tourist_safety.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE tourists (id INTEGER PRIMARY KEY, tourist_code VARCHAR(50) UNIQUE NOT NULL, name VARCHAR(100) NOT NULL,
            phone VARCHAR(20), enrollment_number VARCHAR(50) UNIQUE, college_email VARCHAR(255) UNIQUE,
            emergency_contact_name VARCHAR(100), emergency_contact_phone VARCHAR(20), emergency_contact_email VARCHAR(255),
            latitude FLOAT, longitude FLOAT, safety_status VARCHAR(20) NOT NULL, last_location_update DATETIME,
            created_at DATETIME NOT NULL);
        CREATE TABLE safety_zones (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL, radius_meters FLOAT NOT NULL, zone_type VARCHAR(30) NOT NULL, description TEXT,
            active BOOLEAN NOT NULL);
        CREATE TABLE sos_alerts (id INTEGER PRIMARY KEY, tourist_code VARCHAR(50) NOT NULL, latitude FLOAT, longitude FLOAT,
            message TEXT, status VARCHAR(20) NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE tourist_access (id INTEGER PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL,
            tourist_code VARCHAR(50) UNIQUE NOT NULL, active BOOLEAN NOT NULL);
    """)
    for i in range(6):
        con.execute("INSERT INTO tourists (tourist_code, name, safety_status, created_at) VALUES (?, ?, 'SAFE', '2026-10-01')",
                    (f"T{i}", f"Fixture {i}"))
    for i in range(209):
        con.execute("INSERT INTO safety_zones (name, latitude, longitude, radius_meters, zone_type, active) "
                    "VALUES (?, 13.0, 77.0, 200, 'RESTRICTED', 1)", (f"Z{i}",))
    for i in range(5):
        con.execute("INSERT INTO sos_alerts (tourist_code, status, created_at) VALUES ('T0', 'OPEN', '2026-10-02')")
    con.commit()
    con.close()

    engine = create_engine(f"sqlite:///{path}")
    report = run_migrations(engine)
    assert report["from_version"] == 1 and report["to_version"] == 3
    assert report["protected_counts_after"] == {"tourists": 6, "safety_zones": 209, "sos_alerts": 5, "tourist_access": 0}
    assert report["backup_file"] and "safety_zones.risk_level" in report["added_columns"]
    columns = {c["name"] for c in inspect(engine).get_columns("sos_alerts")}
    assert {"idempotency_key", "assigned_officer_id"} <= columns

    second = run_migrations(engine)  # idempotent
    assert second["added_columns"] == [] and second["new_tables"] == []

    from pathlib import Path

    restore_sqlite(engine, Path(report["backup_file"]))  # rollback to v1
    columns = {c["name"] for c in inspect(create_engine(f"sqlite:///{path}")).get_columns("sos_alerts")}
    assert "idempotency_key" not in columns
    engine.dispose()
