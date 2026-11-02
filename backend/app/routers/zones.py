"""Safety-zone API: public read, admin write, import/export, validation."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.deps import Principal, require_admin
from app.models.models import SafetyZone
from app.services.audit import audit
from app.services.geodata import (
    RISK_LEVELS,
    ZONE_TYPES,
    audit_zones,
    dedupe_key,
    export_geojson,
    export_kml,
    find_overlaps,
    is_college_demo,
    is_synthetic,
    parse_upload,
)
from app.services.geofence import ZoneShape, evaluate, polygon_centroid_and_radius, validate_geometry

router = APIRouter(prefix="/api/v1/zones", tags=["safety zones"])


def zone_dict(z: SafetyZone) -> dict:
    geometry = None
    if z.geometry_geojson:
        try:
            geometry = json.loads(z.geometry_geojson)
        except ValueError:
            geometry = None
    return {
        "id": z.id,
        "name": z.name,
        "latitude": z.latitude,
        "longitude": z.longitude,
        "radius_meters": z.radius_meters,
        "zone_type": z.zone_type,
        "risk_level": z.risk_level,
        "description": z.description,
        "active": z.active,
        "geometry": geometry,
        "source": z.source,
        "verification_status": z.verification_status,
        "category": z.category,
        "evidence": z.evidence,
        "synthetic": is_synthetic(z.name, z.description),
        "college_demo": is_college_demo(z.name),
        "updated_at": z.updated_at,
    }


class ZoneIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: float | None = Field(default=None, gt=0, le=100000)
    zone_type: str = "RESTRICTED"
    risk_level: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    active: bool = True
    geometry: dict | None = None
    source: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=40)
    evidence: str | None = Field(default=None, max_length=2000)


class ZonePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: float | None = Field(default=None, gt=0, le=100000)
    zone_type: str | None = None
    risk_level: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None
    geometry: dict | None = None
    source: str | None = Field(default=None, max_length=255)
    verification_status: str | None = Field(default=None, max_length=40)
    category: str | None = Field(default=None, max_length=40)
    evidence: str | None = Field(default=None, max_length=2000)


class PointCheck(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


def _validate_enums(zone_type: str | None, risk_level: str | None) -> None:
    if zone_type is not None and zone_type.upper() not in ZONE_TYPES:
        raise HTTPException(422, f"zone_type must be one of {', '.join(sorted(ZONE_TYPES))}")
    if risk_level is not None and risk_level.upper() not in RISK_LEVELS:
        raise HTTPException(422, f"risk_level must be one of {', '.join(sorted(RISK_LEVELS))}")


def _apply_geometry(zone: SafetyZone, geometry: dict) -> None:
    problems = validate_geometry(geometry)
    if problems:
        raise HTTPException(422, "Invalid polygon: " + "; ".join(problems[:5]))
    lat, lon, radius = polygon_centroid_and_radius(geometry)
    zone.geometry_geojson = json.dumps(geometry)
    zone.latitude, zone.longitude, zone.radius_meters = lat, lon, round(radius, 2)


@router.get("")
def list_zones(
    search: str | None = Query(default=None, max_length=100),
    zone_type: str | None = None,
    active: bool | None = None,
    synthetic: bool | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SafetyZone)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(SafetyZone.name.ilike(like), SafetyZone.description.ilike(like)))
    if zone_type:
        q = q.filter(SafetyZone.zone_type == zone_type.upper())
    if active is not None:
        q = q.filter(SafetyZone.active.is_(active))
    rows = [zone_dict(z) for z in q.order_by(SafetyZone.id).all()]
    if synthetic is not None:
        rows = [r for r in rows if r["synthetic"] is synthetic]
    return rows


@router.get("/export")
def export_zones(fmt: str = Query(default="geojson", alias="format", pattern="^(geojson|kml)$"),
                 db: Session = Depends(get_db)):
    zones = db.query(SafetyZone).order_by(SafetyZone.id).all()
    if fmt == "kml":
        return Response(export_kml(zones), media_type="application/vnd.google-earth.kml+xml",
                        headers={"Content-Disposition": 'attachment; filename="safety_zones.kml"'})
    return Response(json.dumps(export_geojson(zones), default=str), media_type="application/geo+json",
                    headers={"Content-Disposition": 'attachment; filename="safety_zones.geojson"'})


@router.get("/overlaps")
def zone_overlaps(only_active: bool = True, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(SafetyZone)
    if only_active:
        q = q.filter_by(active=True)
    shapes = [ZoneShape.from_row(z) for z in q.all()]
    pairs = find_overlaps(shapes, limit=1000)
    return {"pairs": pairs, "count": len(pairs),
            "note": "Circle-based overlap (centre distance < combined radius). Polygon zones use their enclosing circle."}


@router.get("/audit")
def zones_audit(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    return audit_zones(db.query(SafetyZone).all())


@router.post("/check")
def check_point(data: PointCheck, db: Session = Depends(get_db)):
    shapes = [ZoneShape.from_row(z) for z in db.query(SafetyZone).filter_by(active=True).all()]
    r = evaluate(data.latitude, data.longitude, shapes, get_settings().caution_buffer_ratio)
    return {"status": r.status, "inside": r.inside, "nearby": r.nearby, "nearest_restricted": r.nearest}


@router.get("/{zone_id}")
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    z = db.get(SafetyZone, zone_id)
    if z is None:
        raise HTTPException(404, "Zone not found")
    return zone_dict(z)


@router.post("", status_code=201)
def create_zone(data: ZoneIn, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    _validate_enums(data.zone_type, data.risk_level)
    zone = SafetyZone(
        name=data.name, zone_type=data.zone_type.upper(),
        risk_level=data.risk_level.upper() if data.risk_level else None,
        description=data.description, active=data.active, source=data.source or "admin dashboard",
        verification_status="ADMIN_CREATED", category=data.category, evidence=data.evidence,
    )
    if data.geometry:
        _apply_geometry(zone, data.geometry)
    else:
        if data.latitude is None or data.longitude is None or data.radius_meters is None:
            raise HTTPException(422, "Provide latitude, longitude and radius_meters, or a polygon geometry")
        zone.latitude, zone.longitude, zone.radius_meters = data.latitude, data.longitude, data.radius_meters
    key = dedupe_key(zone.name, zone.latitude, zone.longitude)
    for existing in db.query(SafetyZone).filter(SafetyZone.name == zone.name).all():
        if dedupe_key(existing.name, existing.latitude, existing.longitude) == key:
            raise HTTPException(409, f"Zone already exists (id {existing.id})")
    db.add(zone)
    db.flush()
    audit(db, "ZONE_CREATED", "STAFF", principal.subject, f"zone:{zone.id}")
    db.commit()
    return zone_dict(zone)


@router.patch("/{zone_id}")
def update_zone(zone_id: int, data: ZonePatch, principal: Principal = Depends(require_admin),
                db: Session = Depends(get_db)):
    zone = db.get(SafetyZone, zone_id)
    if zone is None:
        raise HTTPException(404, "Zone not found")
    _validate_enums(data.zone_type, data.risk_level)
    changes = data.model_dump(exclude_unset=True)
    before = {k: getattr(zone, k) for k in ("latitude", "longitude", "radius_meters", "zone_type", "active")}
    geometry = changes.pop("geometry", None)
    for key, value in changes.items():
        if key in {"zone_type", "risk_level"} and value:
            value = value.upper()
        setattr(zone, key, value)
    if geometry:
        _apply_geometry(zone, geometry)
    audit(db, "ZONE_UPDATED", "STAFF", principal.subject, f"zone:{zone.id}",
          {"fields": sorted(data.model_dump(exclude_unset=True)), "before": before})
    db.commit()
    return zone_dict(zone)


@router.delete("/{zone_id}")
def delete_zone(
    zone_id: int,
    confirm_name: str = Query(..., description="Must exactly match the zone name"),
    permanent: bool = False,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Default: deactivate (soft delete). permanent=true needs SUPER_ADMIN."""
    zone = db.get(SafetyZone, zone_id)
    if zone is None:
        raise HTTPException(404, "Zone not found")
    if confirm_name != zone.name:
        raise HTTPException(409, "confirm_name does not match the zone name")
    if permanent:
        if principal.role != "SUPER_ADMIN":
            raise HTTPException(403, "Only a super admin can permanently delete zones")
        audit(db, "ZONE_DELETED", "STAFF", principal.subject, f"zone:{zone.id}",
              {"name": zone.name, "lat": zone.latitude, "lon": zone.longitude, "radius": zone.radius_meters})
        db.delete(zone)
        db.commit()
        return {"deleted": True, "id": zone_id}
    zone.active = False
    audit(db, "ZONE_DEACTIVATED", "STAFF", principal.subject, f"zone:{zone.id}")
    db.commit()
    return {"deleted": False, "deactivated": True, "zone": zone_dict(zone)}


@router.post("/import")
async def import_zones(
    file: UploadFile = File(...),
    dry_run: bool = True,
    activate: bool = False,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    raw = await file.read(5 * 1024 * 1024 + 1)
    try:
        parsed = parse_upload(file.filename or "", raw)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(422, "File could not be parsed as GeoJSON or KML")

    existing = {dedupe_key(z.name, z.latitude, z.longitude) for z in db.query(SafetyZone).all()}
    seen, report = set(), {"created": [], "duplicates": [], "invalid": []}
    for zone in parsed:
        if zone.problems:
            report["invalid"].append({"name": zone.name, "problems": zone.problems})
            continue
        key = zone.dedupe_key()
        if key in existing or key in seen:
            report["duplicates"].append({"name": zone.name})
            continue
        seen.add(key)
        report["created"].append({"name": zone.name, "latitude": round(zone.latitude, 6),
                                  "longitude": round(zone.longitude, 6), "radius_meters": zone.radius_meters,
                                  "zone_type": zone.zone_type})
        if not dry_run:
            db.add(SafetyZone(
                name=zone.name, latitude=zone.latitude, longitude=zone.longitude,
                radius_meters=zone.radius_meters, zone_type=zone.zone_type, risk_level=zone.risk_level,
                description=zone.description,
                geometry_geojson=json.dumps(zone.geometry) if zone.geometry else None,
                active=activate, source=f"import:{(file.filename or '')[:200]}",
                verification_status="PENDING_REVIEW",
            ))
    if not dry_run:
        audit(db, "ZONES_IMPORTED", "STAFF", principal.subject, None,
              {"file": file.filename, "created": len(report["created"]), "duplicates": len(report["duplicates"]),
               "invalid": len(report["invalid"])})
        db.commit()
    return {"dry_run": dry_run, "activated": activate and not dry_run,
            **{k: v for k, v in report.items()},
            "summary": {k: len(v) for k, v in report.items()}}


DATASET_ZONE_LAYERS = {"natural_hazards": ("CAUTION", 150), "protected_areas": ("CAUTION", None)}


@router.post("/import-dataset")
def import_dataset_layer(
    layer: str = Query(pattern="^(natural_hazards|protected_areas)$"),
    dry_run: bool = True,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create zones from a processed open-data layer. Always inactive + PENDING_REVIEW:
    these are community-mapped features, not official danger designations."""
    from app.services.datasets import layer_path, read_json
    from app.services.geodata import parse_geojson

    path = layer_path(layer)
    if path is None:
        raise HTTPException(404, "Layer not available — run the dataset pipeline first")
    zone_type, default_radius = DATASET_ZONE_LAYERS[layer]
    data = read_json(path)
    features = []
    for f in data.get("features", []):
        p = dict(f.get("properties") or {})
        p.setdefault("radius_meters", p.get("suggested_radius_m") or default_radius)
        p["zone_type"] = zone_type
        features.append({**f, "properties": p})
    parsed = parse_geojson(json.dumps({"type": "FeatureCollection", "features": features}))
    existing = {dedupe_key(z.name, z.latitude, z.longitude) for z in db.query(SafetyZone).all()}
    created, duplicates, invalid = 0, 0, 0
    for zone, feat in zip(parsed, features):
        if zone.problems:
            invalid += 1
            continue
        key = zone.dedupe_key()
        if key in existing:
            duplicates += 1
            continue
        existing.add(key)
        created += 1
        if not dry_run:
            props = feat["properties"]
            db.add(SafetyZone(
                name=zone.name[:100], latitude=zone.latitude, longitude=zone.longitude, radius_meters=zone.radius_meters,
                zone_type=zone_type, geometry_geojson=json.dumps(zone.geometry) if zone.geometry else None, active=False,
                source=f"OpenStreetMap ({props.get('osm_id')})", verification_status="PENDING_REVIEW",
                category=props.get("category"), evidence=props.get("evidence") or f"OSM {props.get('osm_id')}",
                description=f"{props.get('category', '').title()} from OpenStreetMap; community-mapped, not an official designation.",
            ))
    if not dry_run:
        audit(db, "ZONES_IMPORTED_FROM_DATASET", "STAFF", principal.subject, None,
              {"layer": layer, "created": created, "duplicates": duplicates, "invalid": invalid})
        db.commit()
    return {"layer": layer, "dry_run": dry_run, "created": created, "duplicates": duplicates, "invalid": invalid,
            "note": "Imported zones are inactive and PENDING_REVIEW until an admin verifies and activates them."}
