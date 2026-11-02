"""Facilities CRUD, nearest search, dataset import, weather risk, tourist CRUD."""

import json

from conftest import SUPER, make_tourist, staff_headers

FACILITY_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [77.5611, 13.1700]},
         "properties": {"facility_type": "POLICE", "name": "Fixture Police Station", "osm_id": "node/1"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [77.5700, 13.1665]},
         "properties": {"facility_type": "HOSPITAL", "name": "Fixture Hospital", "osm_id": "node/2", "phone": "108"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [78.5, 14.0]},
         "properties": {"facility_type": "FIRE_STATION", "name": "Far Fire Station", "osm_id": "way/3"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [500, 13]},
         "properties": {"facility_type": "POLICE", "name": "Broken", "osm_id": "node/4"}},
    ],
}


def _import_fixture(client, tmp_path, monkeypatch, admin_headers):
    path = tmp_path / "emergency_facilities.geojson"
    path.write_text(json.dumps(FACILITY_GEOJSON))
    monkeypatch.setenv("DATASETS_DIR", str(tmp_path))
    r = client.post("/api/v1/facilities/import-dataset", headers=admin_headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_dataset_import_is_idempotent(client, admin_headers, tmp_path, monkeypatch):
    first = _import_fixture(client, tmp_path, monkeypatch, admin_headers)
    assert first == {"imported": 3, "updated": 0, "skipped": 1, "file": "emergency_facilities.geojson"}
    second = client.post("/api/v1/facilities/import-dataset", headers=admin_headers).json()
    assert second["imported"] == 0 and second["updated"] == 3


def test_nearest_and_nearby_help(client, admin_headers, tourist_headers, tmp_path, monkeypatch):
    _import_fixture(client, tmp_path, monkeypatch, admin_headers)
    near = client.get("/api/v1/facilities/nearby?lat=13.1665&lon=77.5611&radius_m=5000", headers=tourist_headers).json()
    assert [f["name"] for f in near] == ["Fixture Police Station", "Fixture Hospital"]
    assert near[0]["distance_meters"] < near[1]["distance_meters"]
    only = client.get("/api/v1/facilities/nearby?lat=13.1665&lon=77.5611&type=HOSPITAL", headers=tourist_headers).json()
    assert len(only) == 1 and only[0]["facility_type"] == "HOSPITAL"
    assert client.get("/api/v1/facilities/nearby?lat=13&lon=77&type=NOPE", headers=tourist_headers).status_code == 422

    assert client.get("/api/v1/me/nearby-help", headers=tourist_headers).status_code == 422
    client.post("/api/v1/me/location", headers=tourist_headers, json={"latitude": 13.1665, "longitude": 77.5611})
    help_ = client.get("/api/v1/me/nearby-help", headers=tourist_headers).json()
    assert help_["police"]["name"] == "Fixture Police Station"
    assert help_["hospital"]["name"] == "Fixture Hospital"
    assert help_["fire_station"] is None  # far station is beyond 50 km

    alert = client.post("/api/v1/me/sos", headers=tourist_headers, json={"latitude": 13.1665, "longitude": 77.5611}).json()
    sos_help = client.get(f"/api/v1/sos/{alert['alert']['id']}/nearest-help", headers=admin_headers).json()
    assert sos_help["police"]["name"] == "Fixture Police Station"


def test_facility_crud_and_permissions(client, admin_headers, tourist_headers, police_headers):
    body = {"facility_type": "POLICE", "name": "New Outpost", "latitude": 13.0, "longitude": 77.0, "phone": "100"}
    assert client.post("/api/v1/facilities", headers=police_headers, json=body).status_code == 403
    created = client.post("/api/v1/facilities", headers=admin_headers, json=body).json()
    assert created["source"] == "admin"
    assert client.get(f"/api/v1/facilities/{created['id']}", headers=tourist_headers).json()["name"] == "New Outpost"
    updated = client.patch(f"/api/v1/facilities/{created['id']}", headers=admin_headers, json={"name": "Renamed"}).json()
    assert updated["name"] == "Renamed"
    listing = client.get("/api/v1/facilities?type=POLICE&search=renamed", headers=police_headers).json()
    assert listing["total"] == 1
    stats = client.get("/api/v1/facilities/stats", headers=admin_headers).json()
    assert stats["by_type"] == {"POLICE": 1}
    assert client.delete(f"/api/v1/facilities/{created['id']}", headers=admin_headers).json()["deleted"]
    assert client.get(f"/api/v1/facilities/{created['id']}", headers=admin_headers).status_code == 404
    bad = {**body, "facility_type": "SPACESHIP"}
    assert client.post("/api/v1/facilities", headers=admin_headers, json=bad).status_code == 422


def test_weather_risk_rules_and_unreachable(client, tourist_headers, monkeypatch):
    from app.services import weather

    assert weather.weather_risk({"weather_code": 95, "precipitation": 12})["weather_risk_level"] == "HIGH"
    assert weather.weather_risk({"weather_code": 0, "precipitation": 3})["weather_risk_level"] == "MEDIUM"
    assert weather.weather_risk({"weather_code": 1, "temperature_2m": 30})["weather_risk_level"] == "LOW"

    class Boom:
        @staticmethod
        def get(*a, **k):
            raise ConnectionError("offline")

    weather._CACHE.clear()
    monkeypatch.setattr(weather, "httpx", Boom)
    body = client.get("/api/v1/weather?lat=13.1&lon=77.5", headers=tourist_headers).json()
    assert body["available"] is False


def test_layers_and_dataset_endpoints(client, admin_headers, tmp_path, monkeypatch):
    (tmp_path / "karnataka_districts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    (tmp_path / "analysis_summary.json").write_text(json.dumps({"generated_at": "x", "crime": {}}))
    monkeypatch.setenv("DATASETS_DIR", str(tmp_path))
    assert client.get("/api/v1/datasets/layers/districts").json()["type"] == "FeatureCollection"
    assert client.get("/api/v1/datasets/layers/protected_areas").status_code == 404
    assert client.get("/api/v1/datasets/layers/../../etc").status_code == 404
    info = client.get("/api/v1/datasets", headers=admin_headers).json()
    assert info["available"] and info["layers"]["districts"] is True
    assert client.get("/api/v1/datasets/analysis", headers=admin_headers).json()["generated_at"] == "x"


def test_tourist_update_and_delete(client, admin_headers, tourist_headers):
    r = client.patch("/api/v1/admin/tourists/T-TEST-01", headers=admin_headers, json={"phone": "9000000009", "name": "Renamed"})
    assert r.status_code == 200 and r.json()["name"] == "Renamed"
    assert client.delete("/api/v1/admin/tourists/T-TEST-01?confirm=T-TEST-01", headers=admin_headers).status_code == 403
    sup = staff_headers(client, SUPER)
    assert client.delete("/api/v1/admin/tourists/T-TEST-01?confirm=wrong", headers=sup).status_code == 409
    sos = client.post("/api/v1/me/sos", headers=tourist_headers, json={}).json()
    assert client.delete("/api/v1/admin/tourists/T-TEST-01?confirm=T-TEST-01", headers=sup).status_code == 409
    client.post(f"/api/v1/sos/{sos['alert']['id']}/resolve", headers=admin_headers, json={"outcome": "FALSE_ALARM", "notes": "test"})
    done = client.delete("/api/v1/admin/tourists/T-TEST-01?confirm=T-TEST-01", headers=sup).json()
    assert done["deleted"] and done["access"] == 1
    assert client.get("/api/v1/admin/tourists/T-TEST-01", headers=admin_headers).status_code == 404
    assert client.get("/api/v1/me", headers=tourist_headers).status_code == 401


def test_access_and_staff_delete(client, admin_headers):
    make_tourist(client, code="T-ACC", gmail="access.person@gmail.com")
    rows = client.get("/api/v1/admin/tourist-access", headers=admin_headers).json()
    target = next(r for r in rows if r["tourist_code"] == "T-ACC")
    assert client.delete(f"/api/v1/admin/tourist-access/{target['id']}", headers=admin_headers).json()["deleted"]
    assert client.post("/api/v1/auth/tourist/request-otp", json={"email": "access.person@gmail.com"}).status_code == 403
    staff = client.get("/api/v1/admin/staff", headers=admin_headers).json()
    police = next(s for s in staff if s["role"] == "POLICE")
    admin = next(s for s in staff if s["role"] == "ADMIN")
    assert client.delete(f"/api/v1/admin/staff/{admin['id']}", headers=admin_headers).status_code == 403  # admins cannot delete admins
    assert client.delete(f"/api/v1/admin/staff/{police['id']}", headers=admin_headers).json()["deleted"]


def test_zone_category_and_evidence(client, admin_headers):
    z = client.post("/api/v1/zones", headers=admin_headers, json={
        "name": "Falls edge", "latitude": 13.2, "longitude": 77.4, "radius_meters": 60,
        "zone_type": "HIGH_RISK", "category": "WATERFALL", "evidence": "OSM node/123 waterway=waterfall"}).json()
    assert z["category"] == "WATERFALL" and z["evidence"].startswith("OSM")


def test_import_dataset_layer_as_pending_zones(client, admin_headers, tmp_path, monkeypatch):
    hazards = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [75.5, 13.4]},
         "properties": {"name": "Fixture Falls", "category": "WATERFALL", "osm_id": "node/9", "suggested_radius_m": 150}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [999, 13.4]},
         "properties": {"name": "Broken", "category": "CLIFF", "osm_id": "node/10"}},
    ]}
    (tmp_path / "natural_hazards.geojson").write_text(json.dumps(hazards))
    monkeypatch.setenv("DATASETS_DIR", str(tmp_path))
    dry = client.post("/api/v1/zones/import-dataset?layer=natural_hazards", headers=admin_headers).json()
    assert dry["created"] == 1 and dry["invalid"] == 1 and dry["dry_run"]
    assert client.get("/api/v1/zones?search=Fixture").json() == []
    real = client.post("/api/v1/zones/import-dataset?layer=natural_hazards&dry_run=false", headers=admin_headers).json()
    assert real["created"] == 1
    zone = client.get("/api/v1/zones?search=Fixture").json()[0]
    assert zone["active"] is False and zone["verification_status"] == "PENDING_REVIEW"
    assert zone["category"] == "WATERFALL" and zone["radius_meters"] == 150
    again = client.post("/api/v1/zones/import-dataset?layer=natural_hazards&dry_run=false", headers=admin_headers).json()
    assert again["created"] == 0 and again["duplicates"] == 1
    assert client.post("/api/v1/zones/import-dataset?layer=evil", headers=admin_headers).status_code == 422


def test_real_osm_dataset_imports_and_finds_nearest_police(client, admin_headers, monkeypatch):
    """Runs against the committed open dataset (datasets/application_data), not a fixture."""
    import pytest

    from app.services.datasets import BACKEND

    real = BACKEND.parent / "datasets" / "application_data"
    if not (real / "emergency_facilities.geojson").exists():
        pytest.skip("processed open datasets not present")
    monkeypatch.setenv("DATASETS_DIR", str(real))
    result = client.post("/api/v1/facilities/import-dataset", headers=admin_headers).json()
    assert result["imported"] > 5000 and result["skipped"] == 0
    stats = client.get("/api/v1/facilities/stats", headers=admin_headers).json()["by_type"]
    assert stats["POLICE"] > 300 and stats["HOSPITAL"] > 3000
    # Bengaluru city centre (MG Road) must have a mapped police station within 3 km
    near = client.get("/api/v1/facilities/nearby?lat=12.9756&lon=77.6066&type=POLICE&radius_m=3000", headers=admin_headers).json()
    assert near and near[0]["distance_meters"] < 3000
    for layer in ("districts", "protected_areas", "natural_hazards", "district_risk", "attractions"):
        fc = client.get(f"/api/v1/datasets/layers/{layer}").json()
        assert fc["type"] == "FeatureCollection" and fc["features"], layer
    assert len(client.get("/api/v1/datasets/layers/districts").json()["features"]) == 30
    analysis = client.get("/api/v1/datasets/analysis", headers=admin_headers).json()
    assert analysis["crime"]["years"] == [2022, 2024, 2025]
    assert len(analysis["district_risk"]) == 30
