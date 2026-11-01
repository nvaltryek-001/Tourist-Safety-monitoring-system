"""Original (v1.0) endpoints, kept at their original paths and response shapes.

Change from v1.0: endpoints that expose or modify personal data now require
authentication (they were public before). See docs/API_DOCUMENTATION.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import Principal, get_principal, require_admin, require_staff, require_tourist_or_staff_for
from app.models.models import SafetyZone, SOSAlert, Tourist
from app.services import sos as sos_service
from app.services.audit import audit
from app.services.tracking import ingest_location

router = APIRouter(tags=["legacy v1.0"])


class TouristCreate(BaseModel):
    tourist_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = None
    enrollment_number: str | None = None
    college_email: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_email: str | None = None


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(gt=0, le=100000)
    zone_type: str = "RESTRICTED"
    description: str | None = None


class SOSCreate(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    message: str = "Emergency assistance required"


def _tourist_dict(t: Tourist) -> dict:
    return {
        "tourist_code": t.tourist_code,
        "name": t.name,
        "phone": t.phone,
        "enrollment_number": t.enrollment_number,
        "college_email": t.college_email,
        "emergency_contact_name": t.emergency_contact_name,
        "emergency_contact_phone": t.emergency_contact_phone,
        "emergency_contact_email": t.emergency_contact_email,
        "safety_status": t.safety_status,
    }


@router.get("/")
def home():
    return {
        "message": "Smart Tourist Management System API is running",
        "status": "success",
        "docs": "/docs",
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "smart-tourist-management",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/tourists")
def register_tourist(data: TouristCreate, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Tourist).filter_by(tourist_code=data.tourist_code).first():
        raise HTTPException(status_code=409, detail="Tourist code already exists")
    tourist = Tourist(**data.model_dump())
    db.add(tourist)
    audit(db, "TOURIST_CREATED", "STAFF", principal.subject, f"tourist:{data.tourist_code}")
    db.commit()
    db.refresh(tourist)
    return {"message": "Tourist registered", "tourist": _tourist_dict(tourist)}


@router.get("/tourists")
def list_tourists(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    tourists = db.query(Tourist).order_by(Tourist.id.desc()).all()
    return [
        {**_tourist_dict(t), "latitude": t.latitude, "longitude": t.longitude,
         "last_location_update": t.last_location_update}
        for t in tourists
    ]


@router.post("/tourists/{tourist_code}/location")
def update_location(tourist_code: str, data: LocationUpdate, principal: Principal = Depends(get_principal),
                    db: Session = Depends(get_db)):
    require_tourist_or_staff_for(tourist_code, principal)
    tourist = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    result = ingest_location(db, tourist, data.latitude, data.longitude, data.accuracy)
    return {
        "message": "Location updated",
        "tourist_code": tourist_code,
        "latitude": tourist.latitude,
        "longitude": tourist.longitude,
        "safety_status": tourist.safety_status,
        "restricted_zone_alerts": [
            {"zone_id": z["zone_id"], "zone_name": z["zone_name"], "distance_meters": z["distance_meters"]}
            for z in result["restricted_zone_alerts"]
        ],
        "geofence_events": result["geofence_events"],
    }


@router.post("/zones")
def create_zone(data: ZoneCreate, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if data.zone_type not in {"SAFE", "RESTRICTED"}:
        raise HTTPException(status_code=400, detail="zone_type must be SAFE or RESTRICTED")
    zone = SafetyZone(**data.model_dump(), source="admin api", verification_status="ADMIN_CREATED")
    db.add(zone)
    db.flush()
    audit(db, "ZONE_CREATED", "STAFF", principal.subject, f"zone:{zone.id}")
    db.commit()
    return {"message": "Safety zone created", "zone_id": zone.id}


@router.get("/zones")
def list_zones(db: Session = Depends(get_db)):
    return [
        {"id": z.id, "name": z.name, "latitude": z.latitude, "longitude": z.longitude,
         "radius_meters": z.radius_meters, "zone_type": z.zone_type, "description": z.description,
         "active": z.active}
        for z in db.query(SafetyZone).all()
    ]


@router.post("/tourists/{tourist_code}/sos")
def create_sos(tourist_code: str, data: SOSCreate, principal: Principal = Depends(get_principal),
               db: Session = Depends(get_db)):
    require_tourist_or_staff_for(tourist_code, principal)
    tourist = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    alert, _ = sos_service.create_alert(db, tourist, data.latitude, data.longitude, data.message,
                                        actor_type=principal.actor_type, actor_id=principal.subject)
    results = sos_service.notify_new_alert(db, tourist, alert)
    db.commit()
    db.refresh(alert)
    sos_service.publish(db, alert, "sos.created")
    return {
        "message": "SOS alert recorded",
        "alert_id": alert.id,
        "tourist_code": tourist_code,
        "status": alert.status,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "notification_results": results,
    }


@router.get("/sos")
def list_sos(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    return [
        {"id": a.id, "tourist_code": a.tourist_code, "latitude": a.latitude, "longitude": a.longitude,
         "message": a.message, "status": a.status, "created_at": a.created_at}
        for a in db.query(SOSAlert).order_by(SOSAlert.id.desc()).all()
    ]


@router.get("/register", response_class=HTMLResponse)
def tourist_registration_page():
    return HTMLResponse(REGISTER_PAGE)


REGISTER_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tourist Registration · Smart Tourist Safety</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#f4f6f8;margin:0;padding:24px;color:#14212b}
main{max-width:760px;margin:auto;background:#fff;padding:28px;border-radius:10px;border:1px solid #e1e6ea}
h1{font-size:22px;margin:0 0 4px}p.sub{color:#5b6b77;margin:0 0 20px}h2{font-size:15px;margin-top:22px;text-transform:uppercase;letter-spacing:.06em;color:#5b6b77}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}label{display:block;font-size:13px;font-weight:600}
input{box-sizing:border-box;width:100%;padding:10px;margin-top:6px;border:1px solid #c9d2d9;border-radius:6px;font:inherit}
button{margin-top:22px;padding:11px 18px;background:#0f5c4d;color:#fff;border:0;border-radius:6px;font-weight:600;cursor:pointer}
#result{white-space:pre-wrap;margin-top:16px}.note{background:#fff7e6;border:1px solid #f0d9a8;padding:10px;border-radius:6px;font-size:13px}
@media(max-width:560px){.grid{grid-template-columns:1fr}main{padding:16px}}
</style></head><body><main>
<h1>Tourist registration</h1><p class="sub">Smart Tourist Safety Monitoring — administrator form</p>
<p class="note">Registration is restricted to administrators. Sign in with your admin account below.</p>
<form id="reg">
<h2>Administrator</h2><div class="grid">
<label>Admin email<input name="admin_email" type="email" autocomplete="username" required></label>
<label>Admin password<input name="admin_password" type="password" autocomplete="current-password" required></label></div>
<h2>Tourist</h2><div class="grid">
<label>Tourist ID *<input name="tourist_code" placeholder="T001" required></label>
<label>Full name *<input name="name" required></label>
<label>Enrollment number<input name="enrollment_number"></label>
<label>College email<input name="college_email" type="email"></label>
<label>Phone<input name="phone" type="tel"></label>
<label>Login Gmail (for the app)<input name="login_gmail" type="email" placeholder="name@gmail.com"></label></div>
<h2>Emergency contact</h2><div class="grid">
<label>Contact name<input name="emergency_contact_name"></label>
<label>Contact phone<input name="emergency_contact_phone" type="tel"></label>
<label>Contact email<input name="emergency_contact_email" type="email"></label></div>
<button type="submit">Register tourist</button></form><div id="result" role="status"></div>
<p><a href="/docs">API documentation</a></p>
<script>
const form=document.getElementById('reg');
form.addEventListener('submit',async e=>{e.preventDefault();const out=document.getElementById('result');
const d=Object.fromEntries(new FormData(form).entries());out.textContent='Signing in…';
try{let r=await fetch('/api/v1/auth/staff/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:d.admin_email,password:d.admin_password})});
let b=await r.json();if(!r.ok)throw new Error(b.detail||'Login failed');const token=b.access_token;
delete d.admin_email;delete d.admin_password;for(const k in d){if(d[k]==='')d[k]=null}
r=await fetch('/api/v1/admin/tourists',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify(d)});
b=await r.json();if(!r.ok)throw new Error(typeof b.detail==='string'?b.detail:'Registration failed');
out.textContent='Registered '+b.tourist_code;form.reset();}catch(err){out.textContent='Error: '+err.message}});
</script></main></body></html>"""
