import math
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models.models import Tourist, SafetyZone, SOSAlert

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Tourist Management System API",
    description="Tourist GPS tracking, geo-fencing and SOS management.",
    version="1.0.0",
)


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


class ZoneCreate(BaseModel):
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: float = Field(gt=0, le=100000)
    zone_type: str = "RESTRICTED"
    description: str | None = None


class SOSCreate(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    message: str = "Emergency assistance required"


def distance_meters(lat1, lon1, lat2, lon2):
    radius = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@app.get("/")
def home():
    return {
        "message": "Smart Tourist Management System API is running",
        "status": "success",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "smart-tourist-management",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/tourists")
def register_tourist(data: TouristCreate, db: Session = Depends(get_db)):
    existing = db.query(Tourist).filter_by(tourist_code=data.tourist_code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tourist code already exists")

    tourist = Tourist(
        tourist_code=data.tourist_code,
        name=data.name,
        phone=data.phone,
        enrollment_number=data.enrollment_number,
        college_email=data.college_email,
        emergency_contact_name=data.emergency_contact_name,
        emergency_contact_phone=data.emergency_contact_phone,
        emergency_contact_email=data.emergency_contact_email,
    )
    db.add(tourist)
    db.commit()
    db.refresh(tourist)
    return {"message": "Tourist registered", "tourist": {
        "tourist_code": tourist.tourist_code,
        "name": tourist.name,
        "phone": tourist.phone,
        "enrollment_number": tourist.enrollment_number,
        "college_email": tourist.college_email,
        "emergency_contact_name": tourist.emergency_contact_name,
        "emergency_contact_phone": tourist.emergency_contact_phone,
        "emergency_contact_email": tourist.emergency_contact_email,
        "safety_status": tourist.safety_status,
    }}


@app.get("/tourists")
def list_tourists(db: Session = Depends(get_db)):
    tourists = db.query(Tourist).order_by(Tourist.id.desc()).all()
    return [
        {
            "tourist_code": t.tourist_code,
            "name": t.name,
            "phone": t.phone,
            "enrollment_number": t.enrollment_number,
            "college_email": t.college_email,
            "emergency_contact_name": t.emergency_contact_name,
            "emergency_contact_phone": t.emergency_contact_phone,
            "emergency_contact_email": t.emergency_contact_email,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "safety_status": t.safety_status,
            "last_location_update": t.last_location_update,
        }
        for t in tourists
    ]


@app.post("/tourists/{tourist_code}/location")
def update_location(
    tourist_code: str,
    data: LocationUpdate,
    db: Session = Depends(get_db),
):
    tourist = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")

    tourist.latitude = data.latitude
    tourist.longitude = data.longitude
    tourist.last_location_update = datetime.now(timezone.utc)

    restricted_zones = db.query(SafetyZone).filter_by(
        active=True, zone_type="RESTRICTED"
    ).all()

    nearby_restricted = []
    for zone in restricted_zones:
        distance = distance_meters(
            data.latitude, data.longitude, zone.latitude, zone.longitude
        )
        if distance <= zone.radius_meters:
            nearby_restricted.append({
                "zone_id": zone.id,
                "zone_name": zone.name,
                "distance_meters": round(distance, 2),
            })

    tourist.safety_status = "DANGER" if nearby_restricted else "SAFE"
    db.commit()

    return {
        "message": "Location updated",
        "tourist_code": tourist_code,
        "latitude": tourist.latitude,
        "longitude": tourist.longitude,
        "safety_status": tourist.safety_status,
        "restricted_zone_alerts": nearby_restricted,
    }


@app.post("/zones")
def create_zone(data: ZoneCreate, db: Session = Depends(get_db)):
    if data.zone_type not in {"SAFE", "RESTRICTED"}:
        raise HTTPException(
            status_code=400,
            detail="zone_type must be SAFE or RESTRICTED",
        )

    zone = SafetyZone(
        name=data.name,
        latitude=data.latitude,
        longitude=data.longitude,
        radius_meters=data.radius_meters,
        zone_type=data.zone_type,
        description=data.description,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return {"message": "Safety zone created", "zone_id": zone.id}


@app.get("/zones")
def list_zones(db: Session = Depends(get_db)):
    zones = db.query(SafetyZone).all()
    return [
        {
            "id": z.id,
            "name": z.name,
            "latitude": z.latitude,
            "longitude": z.longitude,
            "radius_meters": z.radius_meters,
            "zone_type": z.zone_type,
            "description": z.description,
            "active": z.active,
        }
        for z in zones
    ]


@app.post("/tourists/{tourist_code}/sos")
def create_sos(
    tourist_code: str,
    data: SOSCreate,
    db: Session = Depends(get_db),
):
    tourist = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")

    latitude = data.latitude if data.latitude is not None else tourist.latitude
    longitude = data.longitude if data.longitude is not None else tourist.longitude

    alert = SOSAlert(
        tourist_code=tourist_code,
        latitude=latitude,
        longitude=longitude,
        message=data.message,
    )
    tourist.safety_status = "SOS"
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message": "SOS alert recorded",
        "alert_id": alert.id,
        "tourist_code": tourist_code,
        "status": alert.status,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
    }


@app.get("/sos")
def list_sos(db: Session = Depends(get_db)):
    alerts = db.query(SOSAlert).order_by(SOSAlert.id.desc()).all()
    return [
        {
            "id": a.id,
            "tourist_code": a.tourist_code,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at,
        }
        for a in alerts
    ]


@app.get("/register", response_class=HTMLResponse)
def tourist_registration_page():
    return HTMLResponse(r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Tourist Management ? Registration</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f6fb;margin:0;padding:24px;color:#172033}
main{max-width:760px;margin:auto;background:white;padding:24px;border-radius:14px;box-shadow:0 4px 20px #0001}
h1{font-size:26px}h2{font-size:18px;margin-top:24px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
label{display:block;font-size:14px;font-weight:bold}
input{box-sizing:border-box;width:100%;padding:11px;margin-top:6px;border:1px solid #cbd5e1;border-radius:7px}
button{margin-top:22px;padding:12px 18px;background:#1769e0;color:white;border:0;border-radius:8px;font-weight:bold;cursor:pointer}
#result{white-space:pre-wrap;margin-top:16px}
@media(max-width:560px){.grid{grid-template-columns:1fr}main{padding:16px}}
</style>
</head>
<body><main>
<h1>Smart Tourist Management System</h1>
<p>Tourist Registration</p>
<form id="reg">
<h2>Tourist details</h2><div class="grid">
<label>Tourist ID *<input name="tourist_code" placeholder="T001" required></label>
<label>Full name *<input name="name" required></label>
<label>Enrollment number *<input name="enrollment_number" required></label>
<label>College email *<input name="college_email" type="email" required></label>
<label>Phone *<input name="phone" type="tel" required></label>
</div>
<h2>Emergency contact</h2><div class="grid">
<label>Contact name *<input name="emergency_contact_name" required></label>
<label>Contact phone *<input name="emergency_contact_phone" type="tel" required></label>
<label>Contact email *<input name="emergency_contact_email" type="email" required></label>
</div>
<button type="submit">Register Tourist</button>
</form><div id="result" role="status"></div>
<p><a href="/docs">Open API documentation</a> ? <a href="/tourists">View registered tourists (JSON)</a></p>
<script>
const form=document.getElementById('reg');
form.addEventListener('submit',async e=>{
 e.preventDefault();
 const result=document.getElementById('result');
 const data=Object.fromEntries(new FormData(form).entries());
 result.textContent='Registering...';
 try{
  const r=await fetch('/tourists',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const body=await r.json();
  if(!r.ok) throw new Error(body.detail||'Registration failed');
  result.textContent='Registration successful: '+data.tourist_code;
  form.reset();
 }catch(err){result.textContent='Error: '+err.message;}
});
</script>
</main></body></html>
""")
