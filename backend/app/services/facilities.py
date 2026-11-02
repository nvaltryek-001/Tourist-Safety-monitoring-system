"""Emergency facility import and nearest-facility search."""

from __future__ import annotations

import math
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.models import EmergencyFacility
from app.services.datasets import layer_path, read_json
from app.services.geofence import distance_meters, valid_coordinate

TYPES = ("POLICE", "HOSPITAL", "CLINIC", "FIRE_STATION", "PHARMACY")


def facility_dict(f: EmergencyFacility, distance: float | None = None) -> dict:
    data = {
        "id": f.id, "facility_type": f.facility_type, "name": f.name, "latitude": f.latitude,
        "longitude": f.longitude, "phone": f.phone, "address": f.address, "district": f.district,
        "opening_hours": f.opening_hours, "emergency": f.emergency, "source": f.source,
        "source_ref": f.source_ref, "active": f.active, "updated_at": f.updated_at,
    }
    if distance is not None:
        data["distance_meters"] = round(distance, 1)
    return data


def import_geojson(db: Session, path: Path | None = None) -> dict:
    """Upsert facilities from the processed OSM GeoJSON. Admin edits to name/phone are kept."""
    path = path or layer_path("facilities")
    if path is None:
        return {"imported": 0, "updated": 0, "skipped": 0, "error": "facility dataset not found"}
    features = read_json(path).get("features", [])
    existing = {(f.source, f.source_ref): f for f in db.query(EmergencyFacility).filter(EmergencyFacility.source == "osm").all()}
    imported = updated = skipped = 0
    for feat in features:
        props = feat.get("properties") or {}
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        ftype = (props.get("facility_type") or "").upper()
        if len(coords) < 2 or not valid_coordinate(coords[1], coords[0]) or ftype not in TYPES:
            skipped += 1
            continue
        key = ("osm", props.get("osm_id"))
        row = existing.get(key)
        if row is None:
            db.add(EmergencyFacility(
                facility_type=ftype, name=(props.get("name") or ftype.title())[:200], latitude=coords[1],
                longitude=coords[0], phone=(props.get("phone") or None), address=(props.get("address") or None),
                district=props.get("district"), opening_hours=props.get("opening_hours"),
                emergency=props.get("emergency"), source="osm", source_ref=props.get("osm_id"),
            ))
            imported += 1
        else:
            row.latitude, row.longitude, row.district = coords[1], coords[0], props.get("district")
            updated += 1
    db.commit()
    return {"imported": imported, "updated": updated, "skipped": skipped, "file": path.name}


def nearest(db: Session, lat: float, lon: float, types: list[str] | None = None, limit: int = 5,
            radius_m: float = 25000) -> list[dict]:
    """Nearest active facilities using a bounding-box pre-filter then Haversine."""
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(0.2, math.cos(math.radians(lat))))
    q = db.query(EmergencyFacility).filter(
        EmergencyFacility.active.is_(True),
        EmergencyFacility.latitude.between(lat - dlat, lat + dlat),
        EmergencyFacility.longitude.between(lon - dlon, lon + dlon),
    )
    if types:
        q = q.filter(EmergencyFacility.facility_type.in_(types))
    scored = [(distance_meters(lat, lon, f.latitude, f.longitude), f) for f in q.all()]
    scored = [s for s in scored if s[0] <= radius_m]
    scored.sort(key=lambda s: s[0])
    return [facility_dict(f, d) for d, f in scored[:limit]]


def nearest_by_type(db: Session, lat: float, lon: float, radius_m: float = 50000) -> dict:
    out = {}
    for t in ("POLICE", "HOSPITAL", "FIRE_STATION"):
        hit = nearest(db, lat, lon, [t] if t != "HOSPITAL" else ["HOSPITAL", "CLINIC"], 1, radius_m)
        out[t.lower()] = hit[0] if hit else None
    return out
