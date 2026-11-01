from conftest import make_tourist


def test_consent_required_for_location(client):
    headers = make_tourist(client, consent=False)
    r = client.post("/api/v1/me/location", headers=headers, json={"latitude": 13.0, "longitude": 77.0})
    assert r.status_code == 403


def test_invalid_coordinates_rejected(client, tourist_headers):
    r = client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 95, "longitude": 77.0})
    assert r.status_code == 422


def test_geofence_entry_and_exit(client, tourist_headers, restricted_zone, admin_headers):
    inside = client.post("/api/v1/me/location", headers=tourist_headers,
                         json={"latitude": 13.0, "longitude": 77.0, "accuracy": 8})
    body = inside.json()
    assert body["safety_status"] == "DANGER"
    assert body["geofence_events"][0]["event_type"] == "ENTER"

    again = client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.0001, "longitude": 77.0})
    assert again.json()["geofence_events"] == []

    out = client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.05, "longitude": 77.05})
    assert out.json()["safety_status"] == "SAFE"
    assert out.json()["geofence_events"][0]["event_type"] == "EXIT"

    notes = client.get("/api/v1/me/notifications", headers=tourist_headers).json()
    assert any(n["category"] == "RESTRICTED_ZONE_ENTRY" for n in notes)

    status = client.get("/api/v1/me/status", headers=tourist_headers).json()
    assert status["display_state"] == "SAFE" and status["location_state"] == "LIVE"

    detail = client.get("/api/v1/admin/tourists/T-TEST-01", headers=admin_headers).json()
    assert len(detail["geofence_events"]) == 2


def test_status_without_location_is_not_safe(client, tourist_headers):
    status = client.get("/api/v1/me/status", headers=tourist_headers).json()
    assert status["display_state"] == "LOCATION_UNAVAILABLE"


def test_offline_batch_deduplicates(client, tourist_headers):
    points = [
        {"latitude": 13.1, "longitude": 77.1, "recorded_at": "2026-11-01T10:00:00Z", "client_id": "a1"},
        {"latitude": 13.11, "longitude": 77.1, "recorded_at": "2026-11-01T10:01:00Z", "client_id": "a2"},
    ]
    first = client.post("/api/v1/me/locations/batch", headers=tourist_headers, json={"points": points}).json()
    assert first["accepted"] == 2
    second = client.post("/api/v1/me/locations/batch", headers=tourist_headers, json={"points": points}).json()
    assert second == {"accepted": 0, "duplicates": 2, "latest": None}
    history = client.get("/api/v1/me/locations?hours=720", headers=tourist_headers).json()
    assert len(history) == 2


def test_older_point_does_not_overwrite_latest(client, tourist_headers):
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.2, "longitude": 77.2})
    client.post("/api/v1/me/location", headers=tourist_headers,
                json={"latitude": 13.3, "longitude": 77.3, "recorded_at": "2020-01-01T00:00:00Z"})
    me = client.get("/api/v1/me", headers=tourist_headers).json()
    assert me["latitude"] == 13.2


def test_legacy_location_endpoint_requires_owner(client, tourist_headers):
    other = make_tourist(client, code="T-OTHER", gmail="other.person@gmail.com")
    assert client.post("/tourists/T-TEST-01/location", json={"latitude": 13, "longitude": 77}).status_code == 401
    assert client.post("/tourists/T-TEST-01/location", headers=other,
                       json={"latitude": 13, "longitude": 77}).status_code == 403
    r = client.post("/tourists/T-TEST-01/location", headers=tourist_headers, json={"latitude": 13, "longitude": 77})
    assert r.status_code == 200 and r.json()["message"] == "Location updated"


def test_trips(client, tourist_headers):
    trip = client.post("/api/v1/me/trips", headers=tourist_headers, json={"title": "Nandi Hills"}).json()
    assert client.post("/api/v1/me/trips", headers=tourist_headers, json={"title": "Second"}).status_code == 409
    assert client.get("/api/v1/me/status", headers=tourist_headers).json()["active_trip"]["id"] == trip["id"]
    assert client.post(f"/api/v1/me/trips/{trip['id']}/end", headers=tourist_headers).json()["status"] == "COMPLETED"


def test_delete_own_history_and_safety_report(client, tourist_headers):
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.2, "longitude": 77.2})
    report = client.get("/api/v1/me/safety-report", headers=tourist_headers).json()
    assert report["kind"] == "AI_ADVISORY"
    assert client.delete("/api/v1/me/locations", headers=tourist_headers).json()["deleted"] == 1


def test_profile_update_push_token(client, tourist_headers):
    r = client.patch("/api/v1/me", headers=tourist_headers, json={"expo_push_token": "ExponentPushToken[test]"})
    assert r.json()["push_registered"] is True
