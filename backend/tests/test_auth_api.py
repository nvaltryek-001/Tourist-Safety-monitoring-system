from conftest import ADMIN, POLICE, SUPER, make_tourist, staff_headers


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/ready").json()["database"] == "ok"
    assert client.get("/").json()["status"] == "success"


def test_tourist_otp_login_flow(client):
    headers = make_tourist(client)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["role"] == "TOURIST" and me["tourist_code"] == "T-TEST-01"


def test_otp_response_is_honest_about_delivery(client, admin_headers):
    client.post("/api/v1/admin/tourists", headers=admin_headers,
                json={"tourist_code": "T-X", "name": "X", "login_gmail": "x.person@gmail.com"})
    body = client.post("/api/v1/auth/tourist/request-otp", json={"email": "x.person@gmail.com"}).json()
    assert body["delivery"] == "NOT_CONFIGURED"
    assert "NOT emailed" in body["message"]


def test_non_gmail_and_unapproved_rejected(client):
    assert client.post("/api/v1/auth/tourist/request-otp", json={"email": "someone@yahoo.com"}).status_code == 422
    assert client.post("/api/v1/auth/tourist/request-otp", json={"email": "stranger.abc@gmail.com"}).status_code == 403


def test_wrong_and_reused_otp(client, admin_headers):
    client.post("/api/v1/admin/tourists", headers=admin_headers,
                json={"tourist_code": "T-OTP", "name": "Otp", "login_gmail": "otp.user@gmail.com"})
    code = client.post("/api/v1/auth/tourist/request-otp", json={"email": "otp.user@gmail.com"}).json()["dev_otp"]
    wrong = "000000" if code != "000000" else "111111"
    assert client.post("/api/v1/auth/tourist/verify-otp", json={"email": "otp.user@gmail.com", "code": wrong}).status_code == 401
    ok = client.post("/api/v1/auth/tourist/verify-otp", json={"email": "otp.user@gmail.com", "code": code})
    assert ok.status_code == 200
    again = client.post("/api/v1/auth/tourist/verify-otp", json={"email": "otp.user@gmail.com", "code": code})
    assert again.status_code == 401


def test_otp_request_rate_limited(client, admin_headers):
    client.post("/api/v1/admin/tourists", headers=admin_headers,
                json={"tourist_code": "T-RL", "name": "Rl", "login_gmail": "rate.limit@gmail.com"})
    codes = [client.post("/api/v1/auth/tourist/request-otp", json={"email": "rate.limit@gmail.com"}).status_code
             for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_gmail_dot_variant_matches_same_account(client, admin_headers):
    client.post("/api/v1/admin/tourists", headers=admin_headers,
                json={"tourist_code": "T-DOT", "name": "Dot", "login_gmail": "dot.user@gmail.com"})
    assert client.post("/api/v1/auth/tourist/request-otp", json={"email": "DotUser@gmail.com"}).status_code == 200


def test_staff_login_and_lockout(client):
    assert client.post("/api/v1/auth/staff/login", json={"email": ADMIN[0], "password": "bad"}).status_code == 401
    for _ in range(5):
        client.post("/api/v1/auth/staff/login", json={"email": POLICE[0], "password": "bad"})
    assert client.post("/api/v1/auth/staff/login", json={"email": POLICE[0], "password": POLICE[1]}).status_code == 423


def test_logout_revokes_token(client):
    headers = staff_headers(client, ADMIN)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_session_list_and_revoke_others(client):
    first = staff_headers(client, ADMIN)
    second = staff_headers(client, ADMIN)
    sessions = client.get("/api/v1/auth/sessions", headers=second).json()
    assert len(sessions) >= 2
    assert client.post("/api/v1/auth/sessions/revoke-others", headers=second).json()["revoked"] >= 1
    assert client.get("/api/v1/auth/me", headers=first).status_code == 401
    assert client.get("/api/v1/auth/me", headers=second).status_code == 200


def test_authorization_boundaries(client, tourist_headers, police_headers):
    assert client.get("/api/v1/admin/tourists").status_code == 401
    assert client.get("/api/v1/admin/tourists", headers=tourist_headers).status_code == 403
    assert client.get("/tourists", headers=tourist_headers).status_code == 403
    assert client.get("/api/v1/admin/staff", headers=police_headers).status_code == 403
    assert client.get("/api/v1/admin/tourists", headers=police_headers).status_code == 200
    assert client.get("/api/v1/me", headers=police_headers).status_code == 403


def test_only_super_admin_creates_admins(client, admin_headers):
    payload = {"email": "new.admin@example.invalid", "name": "New", "role": "ADMIN", "password": "StrongPass123"}
    assert client.post("/api/v1/admin/staff", headers=admin_headers, json=payload).status_code == 403
    sup = staff_headers(client, SUPER)
    assert client.post("/api/v1/admin/staff", headers=sup, json=payload).status_code == 201
    police = {**payload, "email": "cop@example.invalid", "role": "POLICE"}
    assert client.post("/api/v1/admin/staff", headers=admin_headers, json=police).status_code == 201
    weak = {**police, "email": "weak@example.invalid", "password": "weakpassword"}
    assert client.post("/api/v1/admin/staff", headers=admin_headers, json=weak).status_code == 422


def test_change_password(client):
    headers = staff_headers(client, POLICE)
    r = client.post("/api/v1/auth/staff/change-password", headers=headers,
                    json={"current_password": POLICE[1], "new_password": "NewPolice12345"})
    assert r.status_code == 200
    assert client.post("/api/v1/auth/staff/login",
                       json={"email": POLICE[0], "password": "NewPolice12345"}).status_code == 200


def test_police_sees_masked_contact_details(client, tourist_headers, police_headers):
    items = client.get("/api/v1/admin/tourists", headers=police_headers).json()["items"]
    assert items[0]["emergency_contact_email"].startswith("co***@")
    assert items[0]["enrollment_number"] is None


def test_demo_passwords_are_generated_when_not_configured(tmp_path, monkeypatch):
    """Without DEMO_*_PASSWORD env vars, random policy-compliant passwords are written to a local file."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app import bootstrap
    from app.core.config import reset_settings_cache
    from app.core.security import password_problems, verify_password
    from app.database import Base
    from app.models.models import StaffUser

    for name in ("DEMO_SUPERADMIN_PASSWORD", "DEMO_ADMIN_PASSWORD", "DEMO_POLICE_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(bootstrap, "CREDENTIALS_FILE", tmp_path / "demo_credentials.txt")
    reset_settings_cache()
    engine = create_engine(f"sqlite:///{tmp_path}/demo.db")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        created = bootstrap.bootstrap_staff(db)
        assert len(created) == 3
        lines = [line.split() for line in (tmp_path / "demo_credentials.txt").read_text().splitlines() if not line.startswith("#")]
        assert len(lines) == 3
        for role, email, password in lines:
            assert not password_problems(password)
            assert password not in {"Admin@12345", "SuperAdmin@123", "Police@12345"}
            assert verify_password(password, db.query(StaffUser).filter_by(email=email).one().password_hash)
        assert bootstrap.bootstrap_staff(db) == []  # existing accounts are never overwritten
    finally:
        db.close()
        engine.dispose()
        reset_settings_cache()


def test_forged_forwarded_for_cannot_bypass_rate_limit(client, admin_headers, monkeypatch):
    """Rotating a fake X-Forwarded-For must not reset the per-IP OTP limit."""
    from app.core.config import reset_settings_cache

    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    reset_settings_cache()
    codes = [
        client.post("/api/v1/auth/tourist/request-otp", json={"email": f"nobody{i}@gmail.com"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code
        for i in range(12)
    ]
    assert codes[:10] == [403] * 10 and 429 in codes[10:]


def test_trusted_proxy_uses_rightmost_forwarded_address(monkeypatch):
    from starlette.requests import Request

    from app.core.config import reset_settings_cache
    from app.deps import client_ip

    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"6.6.6.6, 203.0.113.9")], "client": ("10.1.1.1", 1234)}
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    reset_settings_cache()
    assert client_ip(Request(scope)) == "10.1.1.1"
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")
    reset_settings_cache()
    try:
        assert client_ip(Request(scope)) == "203.0.113.9"
    finally:
        monkeypatch.delenv("TRUST_PROXY_HEADERS")
        reset_settings_cache()
