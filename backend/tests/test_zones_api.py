import json

SQUARE = {"type": "Polygon", "coordinates": [[[77.0, 13.0], [77.01, 13.0], [77.01, 13.01], [77.0, 13.01], [77.0, 13.0]]]}


def test_zone_crud_and_permissions(client, admin_headers, tourist_headers):
    payload = {"name": "Cliff Edge", "latitude": 13.37, "longitude": 77.68, "radius_meters": 50,
               "zone_type": "RESTRICTED", "risk_level": "HIGH"}
    assert client.post("/api/v1/zones", headers=tourist_headers, json=payload).status_code == 403
    zone = client.post("/api/v1/zones", headers=admin_headers, json=payload).json()
    assert zone["risk_level"] == "HIGH" and zone["synthetic"] is False
    assert client.post("/api/v1/zones", headers=admin_headers, json=payload).status_code == 409
    assert client.get("/api/v1/zones?search=cliff").json()[0]["id"] == zone["id"]
    patched = client.patch(f"/api/v1/zones/{zone['id']}", headers=admin_headers, json={"radius_meters": 75}).json()
    assert patched["radius_meters"] == 75
    assert client.delete(f"/api/v1/zones/{zone['id']}?confirm_name=wrong", headers=admin_headers).status_code == 409
    soft = client.delete(f"/api/v1/zones/{zone['id']}?confirm_name=Cliff Edge", headers=admin_headers).json()
    assert soft["deactivated"] and client.get(f"/api/v1/zones/{zone['id']}").json()["active"] is False
    hard = client.delete(f"/api/v1/zones/{zone['id']}?confirm_name=Cliff Edge&permanent=true", headers=admin_headers)
    assert hard.status_code == 403  # admin is not super admin


def test_invalid_enum_and_polygon(client, admin_headers):
    bad_type = {"name": "X", "latitude": 1, "longitude": 1, "radius_meters": 10, "zone_type": "WHATEVER"}
    assert client.post("/api/v1/zones", headers=admin_headers, json=bad_type).status_code == 422
    bowtie = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    assert client.post("/api/v1/zones", headers=admin_headers, json={"name": "B", "geometry": bowtie}).status_code == 422
    poly = client.post("/api/v1/zones", headers=admin_headers, json={"name": "Square", "geometry": SQUARE}).json()
    assert poly["geometry"]["type"] == "Polygon" and poly["radius_meters"] > 0
    check = client.post("/api/v1/zones/check", json={"latitude": 13.005, "longitude": 77.005}).json()
    assert check["status"] == "DANGER"


def test_geojson_import_dry_run_then_commit_with_duplicates(client, admin_headers):
    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "Imp A", "radius_meters": 80},
         "geometry": {"type": "Point", "coordinates": [77.1, 13.1]}},
        {"type": "Feature", "properties": {"name": "Imp A", "radius_meters": 80},
         "geometry": {"type": "Point", "coordinates": [77.1, 13.1]}},
        {"type": "Feature", "properties": {"name": "Broken"}, "geometry": {"type": "Point", "coordinates": [999, 1]}},
    ]}
    files = {"file": ("zones.geojson", json.dumps(fc), "application/geo+json")}
    dry = client.post("/api/v1/zones/import?dry_run=true", headers=admin_headers, files=files).json()
    assert dry["summary"] == {"created": 1, "duplicates": 1, "invalid": 1}
    assert client.get("/api/v1/zones?search=Imp").json() == []
    real = client.post("/api/v1/zones/import?dry_run=false", headers=admin_headers, files=files).json()
    assert real["summary"]["created"] == 1
    imported = client.get("/api/v1/zones?search=Imp").json()
    assert len(imported) == 1 and imported[0]["active"] is False
    again = client.post("/api/v1/zones/import?dry_run=false", headers=admin_headers, files=files).json()
    assert again["summary"]["created"] == 0 and again["summary"]["duplicates"] == 2


def test_kml_import_and_export(client, admin_headers):
    kml = ('<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
           '<Placemark><name>Kml Zone</name><Point><coordinates>77.2,13.2</coordinates></Point></Placemark>'
           '</Document></kml>')
    r = client.post("/api/v1/zones/import?dry_run=false&activate=true", headers=admin_headers,
                    files={"file": ("z.kml", kml, "application/vnd.google-earth.kml+xml")})
    assert r.json()["summary"]["created"] == 1
    geo = client.get("/api/v1/zones/export?format=geojson").json()
    assert any(f["properties"]["name"] == "Kml Zone" for f in geo["features"])
    exported = client.get("/api/v1/zones/export?format=kml")
    assert exported.status_code == 200 and "<Placemark>" in exported.text
    bad = client.post("/api/v1/zones/import", headers=admin_headers, files={"file": ("x.txt", "hi", "text/plain")})
    assert bad.status_code == 422


def test_overlaps_and_data_audit(client, admin_headers):
    for i, lat in enumerate((13.5, 13.5005)):
        client.post("/api/v1/zones", headers=admin_headers, json={
            "name": f"College Demo Zone 0{i + 1}", "latitude": lat, "longitude": 77.5, "radius_meters": 200,
            "zone_type": "RESTRICTED"})
    overlaps = client.get("/api/v1/zones/overlaps", headers=admin_headers).json()
    assert overlaps["count"] == 1
    audit = client.get("/api/v1/admin/data-audit", headers=admin_headers).json()
    assert audit["zones"]["college_demo_zones"] == 2
    assert audit["zones"]["college_demo_radii_found"] == [200.0]
    assert audit["zones"]["college_demo_overlaps"]


def test_legacy_zone_routes(client, admin_headers):
    assert client.post("/zones", json={"name": "L", "latitude": 1, "longitude": 1, "radius_meters": 5}).status_code == 401
    r = client.post("/zones", headers=admin_headers, json={"name": "L", "latitude": 1, "longitude": 1, "radius_meters": 5})
    assert r.json()["message"] == "Safety zone created"
    assert client.get("/zones").json()[0]["name"] == "L"
