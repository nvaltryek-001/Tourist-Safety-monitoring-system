"""In-process performance smoke test (TestClient + SQLite, single worker).

It is NOT a production load test; it checks that 100 tourists x 3 location
updates and an SOS burst complete and records the timings to perf.txt so CI
can publish them. Use app/scripts/load_test.py against a deployed server for
real numbers.
"""
import time
from pathlib import Path

from conftest import staff_headers


def test_location_and_sos_throughput(client, admin_headers):
    from app.core.ratelimit import limiter

    client.post("/api/v1/zones", headers=admin_headers, json={
        "name": "Perf zone", "latitude": 13.0, "longitude": 77.0, "radius_meters": 200, "zone_type": "RESTRICTED"})
    tokens = []
    for i in range(100):
        code, gmail = f"P{i:03d}", f"perf.user{i}@gmail.com"
        client.post("/api/v1/admin/tourists", headers=admin_headers, json={"tourist_code": code, "name": code, "login_gmail": gmail})
        otp = client.post("/api/v1/auth/tourist/request-otp", json={"email": gmail}).json()["dev_otp"]
        token = client.post("/api/v1/auth/tourist/verify-otp", json={"email": gmail, "code": otp}).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/me/consent", headers=headers, json={"granted": True})
        tokens.append(headers)
        limiter.reset()

    start = time.perf_counter()
    for round_ in range(3):
        for i, h in enumerate(tokens):
            r = client.post("/api/v1/me/location", headers=h,
                            json={"latitude": 13.0 + (i % 10) * 0.001, "longitude": 77.0 + round_ * 0.001, "accuracy": 10})
            assert r.status_code == 200
    loc_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    for h in tokens[:20]:
        assert client.post("/api/v1/me/sos", headers=h, json={"message": "burst"}).status_code == 200
    sos_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    assert client.get("/api/v1/analytics/overview", headers=staff_headers(client)).status_code == 200
    overview_ms = (time.perf_counter() - start) * 1000

    line = (f"300 location updates in {loc_elapsed:.2f}s ({loc_elapsed / 300 * 1000:.1f} ms avg); "
            f"20 SOS in {sos_elapsed:.2f}s ({sos_elapsed / 20 * 1000:.1f} ms avg); overview {overview_ms:.0f} ms")
    Path("perf.txt").write_text(line)
    print(line)
