"""Emergency facilities, open-dataset layers, analysis results and weather."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.database import get_db
from app.deps import Principal, get_principal, require_admin, require_staff
from app.models.models import EmergencyFacility, SOSAlert
from app.services import facilities as fac
from app.services import weather
from app.services.audit import audit
from app.services.datasets import LAYERS, analysis_summary, data_dir, layer_path, manifest

router = APIRouter(tags=["facilities, datasets & weather"])


class FacilityIn(BaseModel):
    facility_type: str = Field(pattern="^(POLICE|HOSPITAL|CLINIC|FIRE_STATION|PHARMACY)$")
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=300)
    district: str | None = Field(default=None, max_length=80)
    opening_hours: str | None = Field(default=None, max_length=120)
    emergency: bool | None = None
    active: bool = True


class FacilityPatch(BaseModel):
    facility_type: str | None = Field(default=None, pattern="^(POLICE|HOSPITAL|CLINIC|FIRE_STATION|PHARMACY)$")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=300)
    district: str | None = Field(default=None, max_length=80)
    opening_hours: str | None = Field(default=None, max_length=120)
    emergency: bool | None = None
    active: bool | None = None


def _types(value: str | None) -> list[str] | None:
    if not value:
        return None
    types = [t.strip().upper() for t in value.split(",") if t.strip()]
    bad = [t for t in types if t not in fac.TYPES]
    if bad:
        raise HTTPException(422, f"unknown facility type(s): {', '.join(bad)}")
    return types


# -------------------------------------------------------------- facilities
@router.get("/api/v1/facilities")
def list_facilities(
    facility_type: str | None = Query(default=None, alias="type"),
    search: str | None = Query(default=None, max_length=100),
    district: str | None = Query(default=None, max_length=80),
    active: bool | None = None,
    south: float | None = None, west: float | None = None, north: float | None = None, east: float | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=2000),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    q = db.query(EmergencyFacility)
    types = _types(facility_type)
    if types:
        q = q.filter(EmergencyFacility.facility_type.in_(types))
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(EmergencyFacility.name.ilike(like), EmergencyFacility.address.ilike(like)))
    if district:
        q = q.filter(EmergencyFacility.district.ilike(f"%{district.strip()}%"))
    if active is not None:
        q = q.filter(EmergencyFacility.active.is_(active))
    if None not in (south, west, north, east):
        q = q.filter(EmergencyFacility.latitude.between(south, north), EmergencyFacility.longitude.between(west, east))
    total = q.count()
    rows = q.order_by(EmergencyFacility.facility_type, EmergencyFacility.name).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [fac.facility_dict(f) for f in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/api/v1/facilities/nearby")
def nearby_facilities(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    facility_type: str | None = Query(default=None, alias="type"),
    radius_m: float = Query(default=10000, gt=0, le=100000),
    limit: int = Query(default=10, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return fac.nearest(db, lat, lon, _types(facility_type), limit, radius_m)


@router.get("/api/v1/facilities/stats")
def facility_stats(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    from sqlalchemy import func

    rows = db.query(EmergencyFacility.facility_type, func.count()).filter(EmergencyFacility.active.is_(True)).group_by(
        EmergencyFacility.facility_type).all()
    return {"by_type": {t: n for t, n in rows}, "total": sum(n for _, n in rows)}


@router.get("/api/v1/facilities/{facility_id}")
def get_facility(facility_id: int, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    f = db.get(EmergencyFacility, facility_id)
    if f is None:
        raise HTTPException(404, "Facility not found")
    return fac.facility_dict(f)


@router.post("/api/v1/facilities", status_code=201)
def create_facility(data: FacilityIn, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    f = EmergencyFacility(**data.model_dump(), source="admin")
    db.add(f)
    db.flush()
    audit(db, "FACILITY_CREATED", "STAFF", principal.subject, f"facility:{f.id}")
    db.commit()
    return fac.facility_dict(f)


@router.patch("/api/v1/facilities/{facility_id}")
def update_facility(facility_id: int, data: FacilityPatch, principal: Principal = Depends(require_admin),
                    db: Session = Depends(get_db)):
    f = db.get(EmergencyFacility, facility_id)
    if f is None:
        raise HTTPException(404, "Facility not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(f, key, value)
    f.updated_at = utc_now()
    audit(db, "FACILITY_UPDATED", "STAFF", principal.subject, f"facility:{f.id}",
          {"fields": sorted(data.model_dump(exclude_unset=True))})
    db.commit()
    return fac.facility_dict(f)


@router.delete("/api/v1/facilities/{facility_id}")
def delete_facility(facility_id: int, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    f = db.get(EmergencyFacility, facility_id)
    if f is None:
        raise HTTPException(404, "Facility not found")
    audit(db, "FACILITY_DELETED", "STAFF", principal.subject, f"facility:{f.id}", {"name": f.name, "source": f.source})
    db.delete(f)
    db.commit()
    return {"deleted": True, "id": facility_id}


@router.post("/api/v1/facilities/import-dataset")
def import_facilities(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    result = fac.import_geojson(db)
    audit(db, "FACILITIES_IMPORTED", "STAFF", principal.subject, None, result, commit=True)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


@router.get("/api/v1/sos/{alert_id}/nearest-help")
def sos_nearest_help(alert_id: int, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    alert = db.get(SOSAlert, alert_id)
    if alert is None:
        raise HTTPException(404, "SOS alert not found")
    if alert.latitude is None or alert.longitude is None:
        return {"location": None, "police": None, "hospital": None, "fire_station": None}
    return {"location": {"latitude": alert.latitude, "longitude": alert.longitude},
            **fac.nearest_by_type(db, alert.latitude, alert.longitude)}


@router.get("/api/v1/me/nearby-help")
def my_nearby_help(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    if lat is None or lon is None:
        t = principal.tourist
        if t is None or t.latitude is None:
            raise HTTPException(422, "No location available. Share your location first.")
        lat, lon = t.latitude, t.longitude
    return {
        "location": {"latitude": lat, "longitude": lon},
        **fac.nearest_by_type(db, lat, lon),
        "nearby": fac.nearest(db, lat, lon, None, 15, 15000),
    }


# ----------------------------------------------------------------- datasets
@router.get("/api/v1/datasets")
def datasets_info(principal: Principal = Depends(require_staff)):
    base = data_dir()
    return {
        "available": base is not None,
        "layers": {name: bool(layer_path(name)) for name in LAYERS},
        "manifest": manifest(),
    }


@router.get("/api/v1/datasets/analysis")
def datasets_analysis(principal: Principal = Depends(require_staff)):
    summary = analysis_summary()
    if summary is None:
        raise HTTPException(404, "Dataset analysis has not been generated yet")
    return summary


@router.get("/api/v1/datasets/layers/{name}")
def dataset_layer(name: str):
    """Public GeoJSON layers (open data, no personal information)."""
    path = layer_path(name)
    if path is None:
        raise HTTPException(404, "Layer not available")
    return FileResponse(path, media_type="application/geo+json",
                        headers={"Cache-Control": "public, max-age=3600"})


# ------------------------------------------------------------------ weather
@router.get("/api/v1/weather")
def current_weather(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    principal: Principal = Depends(get_principal),
):
    return weather.current(lat, lon)
