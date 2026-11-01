"""Legacy POST /tourists contract (now admin-only; response shape unchanged)."""


def test_register_tourist_returns_registered_tourist(client, admin_headers):
    response = client.post(
        "/tourists",
        headers=admin_headers,
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


def test_duplicate_tourist_code_returns_conflict(client, admin_headers):
    payload = {"tourist_code": "TEST-TOURIST-DUPLICATE", "name": "Duplicate Test"}
    first = client.post("/tourists", headers=admin_headers, json=payload)
    second = client.post("/tourists", headers=admin_headers, json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Tourist code already exists"


def test_registration_requires_admin(client, police_headers):
    payload = {"tourist_code": "NOPE", "name": "Nope"}
    assert client.post("/tourists", json=payload).status_code == 401
    assert client.post("/tourists", headers=police_headers, json=payload).status_code == 403


def test_register_page_served(client):
    r = client.get("/register")
    assert r.status_code == 200 and "Tourist registration" in r.text
