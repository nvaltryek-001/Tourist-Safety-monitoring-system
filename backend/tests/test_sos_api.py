from conftest import ADMIN, make_tourist, staff_headers


def _sos(client, headers, key=None):
    body = {"latitude": 13.0, "longitude": 77.0, "accuracy": 12, "alert_type": "MEDICAL", "message": "Test only"}
    if key:
        body["idempotency_key"] = key
    return client.post("/api/v1/me/sos", headers=headers, json=body)


def test_sos_created_and_confirmed_by_server(client, tourist_headers, admin_headers):
    r = _sos(client, tourist_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] and body["server_confirmed"]
    assert body["alert"]["status"] == "OPEN"
    assert body["alert"]["timeline"][0]["action"] == "CREATED"
    statuses = {(n["channel"], n.get("recipient_type")): n["status"] for n in body["notification_results"]}
    assert statuses[("email", "admin")] == "NOT_CONFIGURED"
    assert statuses[("email", "emergency_contact")] == "NOT_CONFIGURED"
    assert client.get("/api/v1/me/status", headers=tourist_headers).json()["display_state"] == "EMERGENCY"
    staff_notes = client.get("/api/v1/notifications", headers=admin_headers).json()
    assert any(n["category"] == "SOS_ALERT" for n in staff_notes)


def test_sos_idempotency(client, tourist_headers):
    first = _sos(client, tourist_headers, "key-123").json()
    second = _sos(client, tourist_headers, "key-123").json()
    assert second["created"] is False
    assert first["alert"]["id"] == second["alert"]["id"]


def test_full_incident_lifecycle(client, tourist_headers, admin_headers, police_headers):
    alert_id = _sos(client, tourist_headers).json()["alert"]["id"]
    ack = client.post(f"/api/v1/sos/{alert_id}/acknowledge", headers=admin_headers, json={"note": "seen"})
    assert ack.json()["status"] == "ACKNOWLEDGED"
    officers = client.get("/api/v1/admin/officers", headers=admin_headers).json()
    assigned = client.post(f"/api/v1/sos/{alert_id}/assign", headers=admin_headers,
                           json={"officer_id": officers[0]["id"]}).json()
    assert assigned["assigned_officer"]["id"] == officers[0]["id"]
    mine = client.get("/api/v1/sos?scope=mine", headers=police_headers).json()
    assert [a["id"] for a in mine] == [alert_id]
    responding = client.post(f"/api/v1/sos/{alert_id}/status", headers=police_headers, json={"status": "RESPONDING"})
    assert responding.json()["status"] == "RESPONDING"
    # status endpoint cannot resolve without notes
    assert client.post(f"/api/v1/sos/{alert_id}/status", headers=police_headers,
                       json={"status": "RESOLVED"}).status_code == 422
    resolved = client.post(f"/api/v1/sos/{alert_id}/resolve", headers=police_headers,
                           json={"outcome": "ASSISTED", "notes": "Tourist escorted to safety"}).json()
    assert resolved["status"] == "RESOLVED" and resolved["resolution_outcome"] == "ASSISTED"
    actions = [e["action"] for e in resolved["timeline"]]
    assert actions[:2] == ["CREATED", "ACKNOWLEDGED"] and "ASSIGNED" in actions and actions[-1] == "RESOLVED"

    tourist_view = client.get(f"/api/v1/me/sos/{alert_id}", headers=tourist_headers).json()
    assert tourist_view["status"] == "RESOLVED"
    notes = client.get("/api/v1/me/notifications", headers=tourist_headers).json()
    assert {"SOS_ACKNOWLEDGED", "EMERGENCY_RESPONSE"} <= {n["category"] for n in notes}
    assert client.get("/api/v1/me/status", headers=tourist_headers).json()["display_state"] != "EMERGENCY"
    # no transition out of RESOLVED
    assert client.post(f"/api/v1/sos/{alert_id}/acknowledge", headers=admin_headers).status_code == 409


def test_police_accept_and_isolation(client, tourist_headers, admin_headers, police_headers):
    alert_id = _sos(client, tourist_headers).json()["alert"]["id"]
    accepted = client.post(f"/api/v1/sos/{alert_id}/accept", headers=police_headers).json()
    assert accepted["status"] == "RESPONDING"
    sup_headers = staff_headers(client, ("superadmin@demo.local", "SuperAdmin@123"))
    client.post("/api/v1/admin/staff", headers=sup_headers, json={
        "email": "second.cop@example.invalid", "name": "Second", "role": "POLICE", "password": "SecondCop12345"})
    other = staff_headers(client, ("second.cop@example.invalid", "SecondCop12345"))
    assert client.get(f"/api/v1/sos/{alert_id}", headers=other).status_code == 403
    assert alert_id not in [a["id"] for a in client.get("/api/v1/sos", headers=other).json()]
    assert client.post(f"/api/v1/sos/{alert_id}/accept", headers=admin_headers).status_code == 403


def test_police_location_history_only_during_active_sos(client, tourist_headers, police_headers):
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.4, "longitude": 77.4})
    assert client.get("/api/v1/admin/tourists/T-TEST-01/locations", headers=police_headers).status_code == 403
    _sos(client, tourist_headers)
    assert client.get("/api/v1/admin/tourists/T-TEST-01/locations", headers=police_headers).status_code == 200


def test_tourist_cancel_only_when_open(client, tourist_headers, admin_headers):
    alert_id = _sos(client, tourist_headers).json()["alert"]["id"]
    assert client.post(f"/api/v1/me/sos/{alert_id}/cancel", headers=tourist_headers).json()["status"] == "CANCELLED"
    second = _sos(client, tourist_headers).json()["alert"]["id"]
    client.post(f"/api/v1/sos/{second}/acknowledge", headers=admin_headers)
    assert client.post(f"/api/v1/me/sos/{second}/cancel", headers=tourist_headers).status_code == 409


def test_tourist_cannot_read_other_tourist_sos(client, tourist_headers):
    alert_id = _sos(client, tourist_headers).json()["alert"]["id"]
    other = make_tourist(client, code="T-OTHER", gmail="other.person@gmail.com")
    assert client.get(f"/api/v1/me/sos/{alert_id}", headers=other).status_code == 404


def test_legacy_sos_and_listing(client, tourist_headers):
    r = client.post("/tourists/T-TEST-01/sos", headers=tourist_headers, json={"message": "Legacy"})
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "SOS alert recorded" and body["status"] == "OPEN"
    assert client.get("/sos").status_code == 401
    listing = client.get("/sos", headers=staff_headers(client, ADMIN)).json()
    assert listing[0]["id"] == body["alert_id"]


def test_analytics_and_intelligence(client, tourist_headers, admin_headers, police_headers):
    _sos(client, tourist_headers)
    kpis = client.get("/api/v1/analytics/overview", headers=admin_headers).json()["kpis"]
    assert kpis["registered_tourists"] == 1 and kpis["active_sos"] == 1
    trends = client.get("/api/v1/analytics/trends?days=7", headers=police_headers).json()
    assert trends["total"] == 1
    ai = client.get("/api/v1/intelligence/tourists", headers=admin_headers).json()
    assert ai[0]["risk_level"] in {"HIGH", "CRITICAL"}
    report = client.get("/api/v1/intelligence/report", headers=admin_headers).json()
    assert report["kind"] == "AI_ADVISORY" and report["limitations"]


def test_operational_analytics_endpoints(client, tourist_headers, admin_headers, police_headers, restricted_zone):
    for i in range(5):
        client.post("/api/v1/me/sos", headers=tourist_headers,
                    json={"latitude": 13.0 + i * 0.0001, "longitude": 77.0, "alert_type": "MEDICAL", "idempotency_key": f"hot-{i}"})
    hot = client.get("/api/v1/analytics/hotspots?cell_m=500", headers=police_headers).json()
    assert hot["status"] == "OK" and hot["cells"][0]["count"] >= 5
    alerts = client.get("/api/v1/sos?scope=active", headers=admin_headers).json()
    client.post(f"/api/v1/sos/{alerts[0]['id']}/acknowledge", headers=admin_headers)
    client.post(f"/api/v1/sos/{alerts[0]['id']}/resolve", headers=admin_headers, json={"outcome": "ASSISTED", "notes": "Tourist assisted"})
    rt = client.get("/api/v1/analytics/response-times", headers=admin_headers).json()
    assert rt["acknowledged"] >= 1 and rt["resolved"] == 1 and rt["outcomes"] == {"ASSISTED": 1}
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.0, "longitude": 77.0})
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.05, "longitude": 77.05})
    za = client.get("/api/v1/analytics/zone-activity", headers=admin_headers).json()
    assert za["zones"][0]["entries"] == 1 and za["zones"][0]["exits"] == 1
    mv = client.get("/api/v1/analytics/movement", headers=admin_headers).json()
    assert mv["tourists"][0]["tourist_code"] == "T-TEST-01"
    assert client.get("/api/v1/analytics/movement", headers=police_headers).status_code == 403
    assert client.get("/api/v1/analytics/hotspots", headers=tourist_headers).status_code == 403
