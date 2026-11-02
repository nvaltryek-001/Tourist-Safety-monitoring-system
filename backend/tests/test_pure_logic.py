"""Framework-free unit tests: geofence, geodata, intelligence, security, rate limiting."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.ratelimit import RateLimiter
from app.core.security import (
    create_token,
    decode_token,
    generate_otp,
    hash_otp,
    hash_password,
    normalize_email,
    otp_matches,
    password_problems,
    verify_password,
)
from app.services import geodata, intelligence
from app.services.geofence import (
    ZoneShape,
    distance_meters,
    evaluate,
    point_in_polygon,
    transitions,
    validate_geometry,
    valid_coordinate,
)

SQUARE = {"type": "Polygon", "coordinates": [[[77.0, 13.0], [77.01, 13.0], [77.01, 13.01], [77.0, 13.01], [77.0, 13.0]]]}
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------- geofence
def test_one_degree_latitude_is_about_111_km():
    assert distance_meters(0, 0, 1, 0) == pytest.approx(111_195, rel=1e-3)


@pytest.mark.parametrize("lat,lon,ok", [(0, 0, True), (90, 180, True), (91, 0, False), (0, -181, False),
                                        ("x", 0, False), (float("nan"), 0, False)])
def test_valid_coordinate(lat, lon, ok):
    assert valid_coordinate(lat, lon) is ok


def test_point_in_polygon_with_hole():
    assert point_in_polygon(13.005, 77.005, SQUARE)
    assert not point_in_polygon(13.02, 77.005, SQUARE)
    holed = {"type": "Polygon", "coordinates": SQUARE["coordinates"] + [
        [[77.004, 13.004], [77.006, 13.004], [77.006, 13.006], [77.004, 13.006], [77.004, 13.004]]]}
    assert not point_in_polygon(13.005, 77.005, holed)
    assert point_in_polygon(13.001, 77.001, holed)


def test_validate_geometry_detects_problems():
    assert validate_geometry(SQUARE) == []
    open_ring = {"type": "Polygon", "coordinates": [[[77, 13], [77.1, 13], [77.1, 13.1], [77, 13.1]]]}
    assert any("not closed" in p for p in validate_geometry(open_ring))
    bowtie = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    assert any("self-intersects" in p for p in validate_geometry(bowtie))
    assert validate_geometry({"type": "Point", "coordinates": [0, 0]})


def _zone(id_, lat, lon, r, ztype="RESTRICTED", risk=None, geometry=None):
    return ZoneShape(id_, f"Z{id_}", ztype, lat, lon, r, risk, geometry)


def test_evaluate_statuses():
    zones = [_zone(1, 13.0, 77.0, 100)]
    assert evaluate(13.0, 77.0, zones).status == "DANGER"
    # ~130 m away: outside 100 m but within the 150 m caution buffer
    assert evaluate(13.00117, 77.0, zones).status == "CAUTION"
    assert evaluate(13.1, 77.1, zones).status == "SAFE"
    safe_zone = [_zone(2, 13.0, 77.0, 100, "SAFE")]
    assert evaluate(13.0, 77.0, safe_zone).status == "SAFE"
    medium = [_zone(3, 13.0, 77.0, 100, "SAFE", "MEDIUM")]
    assert evaluate(13.0, 77.0, medium).status == "CAUTION"
    poly = [_zone(4, 13.005, 77.005, 800, geometry=SQUARE)]
    assert evaluate(13.005, 77.005, poly).status == "DANGER"


def test_transitions():
    assert transitions({1, 2}, {2, 3}) == ({3}, {1})


# -------------------------------------------------------------- geodata
def test_geojson_import_parses_points_and_polygons():
    data = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "P", "radius_meters": 50, "zone_type": "restricted"},
         "geometry": {"type": "Point", "coordinates": [77.5, 13.1]}},
        {"type": "Feature", "properties": {"name": "Poly"}, "geometry": SQUARE},
        {"type": "Feature", "properties": {"name": "Bad"}, "geometry": {"type": "Point", "coordinates": [500, 13]}},
    ]}
    zones = geodata.parse_geojson(json.dumps(data))
    assert zones[0].radius_meters == 50 and zones[0].zone_type == "RESTRICTED" and not zones[0].problems
    assert zones[1].geometry and zones[1].radius_meters > 0
    assert zones[2].problems


def test_kml_round_trip_and_dtd_rejected():
    class Z:
        id, name, latitude, longitude, radius_meters = 1, "A & B", 13.1, 77.5, 200
        zone_type, active, description, risk_level, source, geometry_geojson = "RESTRICTED", True, "d", None, None, None

    kml = geodata.export_kml([Z()])
    parsed = geodata.parse_kml(kml)
    assert parsed[0].name == "A & B"
    assert parsed[0].latitude == pytest.approx(13.1)
    with pytest.raises(ValueError):
        geodata.parse_kml('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><kml/>')


def test_parse_upload_rejects_unknown_extension_and_large_files():
    with pytest.raises(ValueError):
        geodata.parse_upload("zones.exe", b"{}")
    with pytest.raises(ValueError):
        geodata.parse_upload("zones.geojson", b"x" * (geodata.MAX_IMPORT_BYTES + 1))


def test_audit_zones_reconciles_synthetic_and_college_demo():
    class Row:
        def __init__(self, id_, name, lat, lon, r, desc=None):
            self.id, self.name, self.latitude, self.longitude, self.radius_meters = id_, name, lat, lon, r
            self.zone_type, self.description, self.active = "RESTRICTED", desc, True
            self.geometry_geojson, self.risk_level = None, None

    rows = [Row(i, f"DEMO-KA-{i:03d}", 12 + i * 0.1, 77, 100, "SYNTHETIC TEST DATA ONLY") for i in range(1, 4)]
    rows += [Row(10, "College Demo Zone 01", 13.0, 77.0, 200), Row(11, "College Demo Zone 02", 13.001, 77.0, 200)]
    rows += [Row(12, "College Demo Zone 02", 13.001, 77.0, 200)]
    report = geodata.audit_zones(rows)
    assert report["synthetic_zones"] == 3
    assert report["college_demo_zones"] == 3
    assert report["college_demo_radii_found"] == [200]
    assert report["college_demo_radius_note"]
    assert report["college_demo_overlaps"]
    assert any(d["kind"] == "name+coordinates" for d in report["duplicates"])


# --------------------------------------------------------- intelligence
def _track(n, start, step_m=0.0, minutes=5):
    return [intelligence.Point(13.0 + i * step_m / 111_000, 77.0, start + timedelta(minutes=minutes * i), 10)
            for i in range(n)]


def test_features_and_stationary_detection():
    pts = _track(12, NOW - timedelta(minutes=60))
    adv, feats = intelligence.rule_checks(pts, [], now=NOW)
    assert feats["stationary_minutes"] >= 45
    assert "PROLONGED_STATIONARY" in {a.code for a in adv}


def test_route_deviation_needs_enough_points():
    assert intelligence.route_deviation(_track(3, NOW)) is None


def test_route_deviation_flags_far_jump():
    pts = _track(10, NOW - timedelta(minutes=50), step_m=20)
    pts.append(intelligence.Point(13.2, 77.0, NOW, 10))  # ~22 km away
    dev = intelligence.route_deviation(pts)
    assert dev["is_anomalous"]


def test_repeated_restricted_entries_and_scoring():
    events = [{"event_type": "ENTER", "zone_id": 1, "zone_name": "Z", "zone_type": "RESTRICTED",
               "created_at": NOW - timedelta(hours=h)} for h in (1, 2)]
    result = intelligence.assess_tourist(_track(3, NOW - timedelta(minutes=10), 200), events, now=NOW)
    codes = {a["code"] for a in result["advisories"]}
    assert {"HIGH_RISK_ENTRY", "REPEATED_RESTRICTED_ENTRY"} <= codes
    assert result["risk_level"] in {"HIGH", "CRITICAL"}
    assert result["confidence"] is None
    assert all(a["kind"] == "AI_ADVISORY" for a in result["advisories"])


def test_stale_and_missing_location():
    old = _track(2, NOW - timedelta(hours=5), 100)
    assert "STALE_LOCATION" in {a["code"] for a in intelligence.assess_tourist(old, [], now=NOW)["advisories"]}
    assert "NO_LOCATION" in {a["code"] for a in intelligence.assess_tourist([], [], now=NOW)["advisories"]}


def test_incident_trends_and_zone_risk():
    alerts = [{"created_at": NOW - timedelta(days=1), "status": "RESOLVED", "alert_type": "MEDICAL",
               "acknowledged_at": NOW - timedelta(days=1) + timedelta(minutes=4), "latitude": 13.0, "longitude": 77.0}]
    trends = intelligence.incident_trends(alerts, days=7, now=NOW)
    assert trends["total"] == 1 and trends["median_ack_minutes"] == 4.0
    assert len(trends["daily"]) == 7
    zones = [{"id": 1, "name": "Z", "latitude": 13.0, "longitude": 77.0, "radius_meters": 100,
              "zone_type": "RESTRICTED", "risk_level": "HIGH"}]
    rows = intelligence.zone_risk(zones, [{"zone_id": 1, "event_type": "ENTER"}], alerts)
    assert rows[0]["risk_index"] == 30 + 20 + 5 + 15


# -------------------------------------------------------------- security
def test_password_hashing():
    h = hash_password("Correct-Horse-9")
    assert verify_password("Correct-Horse-9", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", None)
    assert password_problems("short") and not password_problems("LongEnough123")


def test_otp_and_email_normalisation():
    code = generate_otp()
    assert len(code) == 6 and code.isdigit()
    h = hash_otp("a@gmail.com", code)
    assert otp_matches("a@gmail.com", code, h)
    assert not otp_matches("b@gmail.com", code, h)
    assert normalize_email("First.Last+trip@GoogleMail.com") == "firstlast@gmail.com"


def test_jwt_round_trip():
    token, jti, _ = create_token("T1", "TOURIST", 5)
    payload = decode_token(token)
    assert payload["sub"] == "T1" and payload["jti"] == jti


def test_rate_limiter_window():
    rl = RateLimiter()
    assert rl.hit("k", 2, 10, now=0)
    assert rl.hit("k", 2, 10, now=1)
    assert not rl.hit("k", 2, 10, now=2)
    assert rl.hit("k", 2, 10, now=11)


# ------------------------------------------------------ operational analytics
def test_hotspots_refuse_small_samples_and_cluster_dense_cells():
    few = [{"latitude": 13.0, "longitude": 77.0, "kind": "SOS", "created_at": NOW}] * 3
    assert intelligence.grid_hotspots(few)["status"] == "INSUFFICIENT_DATA"
    dense = [{"latitude": 13.0 + i * 0.0001, "longitude": 77.0, "kind": "SOS", "created_at": NOW} for i in range(4)]
    lone = [{"latitude": 13.5, "longitude": 77.5, "kind": "RESTRICTED_ENTRY", "created_at": NOW}]
    result = intelligence.grid_hotspots(dense + lone, cell_m=500, min_count=2)
    assert result["status"] == "OK" and result["events"] == 5
    assert len(result["cells"]) == 1 and result["cells"][0]["count"] == 4


def test_response_times_and_outcomes():
    alerts = [
        {"created_at": NOW, "acknowledged_at": NOW + timedelta(minutes=2), "resolved_at": NOW + timedelta(minutes=30),
         "status": "RESOLVED", "alert_type": "MEDICAL", "resolution_outcome": "ASSISTED", "officer": "A"},
        {"created_at": NOW, "acknowledged_at": NOW + timedelta(minutes=6), "resolved_at": None,
         "status": "RESPONDING", "alert_type": "GENERAL", "officer": "A"},
        {"created_at": NOW, "acknowledged_at": None, "resolved_at": None, "status": "OPEN"},
    ]
    r = intelligence.response_times(alerts)
    assert r["acknowledged"] == 2 and r["resolved"] == 1
    assert r["ack_minutes"]["median"] == 4.0
    assert r["resolve_minutes"]["median"] == 30.0
    assert r["outcomes"] == {"ASSISTED": 1} and r["resolve_median_by_officer"] == {"A": 30.0}


def test_zone_activity_dwell():
    ev = [
        {"tourist_code": "T1", "zone_id": 1, "zone_name": "Z", "zone_type": "RESTRICTED", "event_type": "ENTER", "created_at": NOW},
        {"tourist_code": "T1", "zone_id": 1, "zone_name": "Z", "zone_type": "RESTRICTED", "event_type": "EXIT", "created_at": NOW + timedelta(minutes=12)},
        {"tourist_code": "T2", "zone_id": 1, "zone_name": "Z", "zone_type": "RESTRICTED", "event_type": "ENTER", "created_at": NOW},
    ]
    rows = intelligence.zone_activity(ev)
    assert rows[0]["entries"] == 2 and rows[0]["unique_tourists"] == 2
    assert rows[0]["median_dwell_minutes"] == 12.0 and rows[0]["currently_inside"] == 1


def test_movement_summary():
    rows = intelligence.movement_summary({"T1": _track(5, NOW, step_m=100)})
    assert rows[0]["points"] == 5 and 0.35 < rows[0]["distance_km"] < 0.45
