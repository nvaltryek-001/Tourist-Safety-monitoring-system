"""Tourist self-service API (the mobile app uses only these + auth + zones)."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.core.security import as_utc, utc_now
from app.database import get_db
from app.deps import Principal, require_tourist
from app.models.models import GeofenceEvent, LocationPoint, Notification, SOSAlert, Trip
from app.services import intelligence
from app.services import sos as sos_service
from app.services.audit import audit
from app.services.geofence import evaluate
from app.services.tracking import ACTIVE_SOS_STATUSES, active_zone_shapes, ingest_location

router = APIRouter(prefix="/api/v1/me", tags=["tourist self-service"])


class LocationIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)
    speed: float | None = Field(default=None, ge=0, le=1000)
    recorded_at: datetime | None = None
    client_id: str | None = Field(default=None, max_length=80)


class LocationBatch(BaseModel):
    points: list[LocationIn] = Field(min_length=1, max_length=200)


class ProfileUpdate(BaseModel):
    expo_push_token: str | None = Field(default=None, max_length=255)
    notify_push: bool | None = None
    notify_email: bool | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    emergency_contact_email: str | None = Field(default=None, max_length=255)


class ConsentIn(BaseModel):
    granted: bool


class SOSIn(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0, le=100000)
    message: str | None = Field(default=None, max_length=500)
    alert_type: str = Field(default="GENERAL", max_length=30)
    idempotency_key: str | None = Field(default=None, max_length=80)


class TripIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    destination: str | None = Field(default=None, max_length=200)
    planned_end_at: datetime | None = None


def profile_dict(t) -> dict:
    return {
        "tourist_code": t.tourist_code,
        "name": t.name,
        "phone": t.phone,
        "college_email": t.college_email,
        "enrollment_number": t.enrollment_number,
        "emergency_contact_name": t.emergency_contact_name,
        "emergency_contact_phone": t.emergency_contact_phone,
        "emergency_contact_email": t.emergency_contact_email,
        "safety_status": t.safety_status,
        "latitude": t.latitude,
        "longitude": t.longitude,
        "location_accuracy": t.location_accuracy,
        "last_location_update": t.last_location_update,
        "location_consent_at": t.location_consent_at,
        "notify_push": t.notify_push is not False,
        "notify_email": t.notify_email is not False,
        "push_registered": bool(t.expo_push_token),
    }


def trip_dict(trip: Trip) -> dict:
    return {
        "id": trip.id, "title": trip.title, "destination": trip.destination, "status": trip.status,
        "started_at": trip.started_at, "ended_at": trip.ended_at, "planned_end_at": trip.planned_end_at,
    }


@router.get("")
def get_profile(p: Principal = Depends(require_tourist)):
    return profile_dict(p.tourist)


@router.patch("")
def update_profile(data: ProfileUpdate, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    t = p.tourist
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    audit(db, "TOURIST_PROFILE_UPDATED", "TOURIST", t.tourist_code, None,
          {"fields": sorted(data.model_dump(exclude_unset=True))})
    db.commit()
    return profile_dict(t)


@router.post("/consent")
def set_consent(data: ConsentIn, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    p.tourist.location_consent_at = utc_now() if data.granted else None
    audit(db, "LOCATION_CONSENT_" + ("GRANTED" if data.granted else "WITHDRAWN"), "TOURIST", p.subject)
    db.commit()
    return {"location_consent_at": p.tourist.location_consent_at}


def _require_consent(p: Principal) -> None:
    if p.tourist.location_consent_at is None:
        raise HTTPException(403, "Location sharing consent has not been given")


@router.post("/location")
def post_location(data: LocationIn, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    _require_consent(p)
    if not limiter.hit(f"loc:{p.subject}", 120, 60):
        raise HTTPException(429, "Too many location updates")
    return ingest_location(db, p.tourist, data.latitude, data.longitude, data.accuracy, data.speed,
                           data.recorded_at, data.client_id)


@router.post("/locations/batch")
def post_location_batch(data: LocationBatch, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    """Offline-queue sync. Each point should carry a client_id so replays are ignored."""
    _require_consent(p)
    if not limiter.hit(f"locbatch:{p.subject}", 20, 60):
        raise HTTPException(429, "Too many batch uploads")
    accepted = duplicates = 0
    last = None
    for point in sorted(data.points, key=lambda x: as_utc(x.recorded_at) or utc_now()):
        result = ingest_location(db, p.tourist, point.latitude, point.longitude, point.accuracy, point.speed,
                                 point.recorded_at, point.client_id)
        if result["duplicate"]:
            duplicates += 1
        else:
            accepted += 1
            last = result
    return {"accepted": accepted, "duplicates": duplicates, "latest": last}


@router.get("/locations")
def my_locations(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    p: Principal = Depends(require_tourist),
    db: Session = Depends(get_db),
):
    since = utc_now() - timedelta(hours=hours)
    rows = (
        db.query(LocationPoint)
        .filter(LocationPoint.tourist_code == p.subject, LocationPoint.recorded_at >= since)
        .order_by(LocationPoint.recorded_at.desc()).limit(2000).all()
    )
    return [
        {"latitude": r.latitude, "longitude": r.longitude, "accuracy": r.accuracy,
         "safety_status": r.safety_status, "recorded_at": r.recorded_at}
        for r in rows
    ]


@router.delete("/locations")
def delete_my_locations(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    count = db.query(LocationPoint).filter_by(tourist_code=p.subject).delete()
    audit(db, "LOCATION_HISTORY_DELETED_BY_TOURIST", "TOURIST", p.subject, None, {"rows": count})
    db.commit()
    return {"deleted": count}


@router.get("/status")
def my_status(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    t = p.tourist
    settings = get_settings()
    zone_eval = None
    location_state = "UNAVAILABLE"
    if t.latitude is not None and t.longitude is not None and t.last_location_update:
        age = (utc_now() - as_utc(t.last_location_update)).total_seconds() / 60
        location_state = "STALE" if age > settings.stale_location_minutes else "LIVE"
        r = evaluate(t.latitude, t.longitude, active_zone_shapes(db), settings.caution_buffer_ratio)
        zone_eval = {"status": r.status, "inside": r.inside, "nearby": r.nearby, "nearest_restricted": r.nearest}
    active_sos = (
        db.query(SOSAlert).filter(SOSAlert.tourist_code == t.tourist_code, SOSAlert.status.in_(ACTIVE_SOS_STATUSES))
        .order_by(SOSAlert.id.desc()).first()
    )
    trip = db.query(Trip).filter_by(tourist_code=t.tourist_code, status="ACTIVE").order_by(Trip.id.desc()).first()
    unread = db.query(Notification).filter_by(recipient_type="TOURIST", recipient_id=t.tourist_code,
                                              channel="IN_APP", read_at=None).count()
    # Display state: never claims SAFE without a live position.
    if active_sos:
        display = "EMERGENCY"
    elif location_state == "UNAVAILABLE":
        display = "LOCATION_UNAVAILABLE"
    elif zone_eval and zone_eval["status"] == "DANGER":
        display = "RESTRICTED"
    elif zone_eval and zone_eval["status"] == "CAUTION":
        display = "CAUTION"
    elif location_state == "STALE":
        display = "LOCATION_STALE"
    else:
        display = "SAFE"
    return {
        "display_state": display,
        "safety_status": t.safety_status,
        "location_state": location_state,
        "last_location_update": t.last_location_update,
        "location": {"latitude": t.latitude, "longitude": t.longitude, "accuracy": t.location_accuracy},
        "zones": zone_eval,
        "active_sos": sos_service.serialize(active_sos, db, include_events=True) if active_sos else None,
        "active_trip": trip_dict(trip) if trip else None,
        "unread_notifications": unread,
        "consent_given": t.location_consent_at is not None,
    }


# --------------------------------------------------------------------- SOS
@router.post("/sos")
def my_sos(data: SOSIn, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    if not limiter.hit(f"sos:{p.subject}", 10, 300):
        raise HTTPException(429, "Too many SOS requests in a short time. Your earlier SOS is still active.")
    alert, created = sos_service.create_alert(
        db, p.tourist, data.latitude, data.longitude, data.message, data.accuracy,
        data.alert_type.upper(), data.idempotency_key,
    )
    results = []
    if created:
        results = sos_service.notify_new_alert(db, p.tourist, alert)
        db.commit()
        db.refresh(alert)
        sos_service.publish(db, alert, "sos.created")
    return {
        "created": created,
        "server_confirmed": True,
        "alert": sos_service.serialize(alert, db, include_events=True),
        "notification_results": results,
    }


@router.get("/sos")
def my_sos_list(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    rows = db.query(SOSAlert).filter_by(tourist_code=p.subject).order_by(SOSAlert.id.desc()).limit(50).all()
    return [sos_service.serialize(a, db) for a in rows]


@router.get("/sos/{alert_id}")
def my_sos_detail(alert_id: int, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    alert = db.get(SOSAlert, alert_id)
    if alert is None or alert.tourist_code != p.subject:
        raise HTTPException(404, "SOS alert not found")
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/sos/{alert_id}/cancel")
def my_sos_cancel(alert_id: int, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    alert = db.get(SOSAlert, alert_id)
    if alert is None or alert.tourist_code != p.subject:
        raise HTTPException(404, "SOS alert not found")
    if alert.status != "OPEN":
        raise HTTPException(409, "Only an SOS that has not been acknowledged yet can be cancelled from the app")
    alert = sos_service.transition(db, alert, "CANCELLED", "TOURIST", p.subject, p.name, "Cancelled by tourist")
    return sos_service.serialize(alert, db, include_events=True)


# ------------------------------------------------------------------- trips
@router.get("/trips")
def my_trips(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    return [trip_dict(t) for t in db.query(Trip).filter_by(tourist_code=p.subject).order_by(Trip.id.desc()).limit(50)]


@router.post("/trips")
def start_trip(data: TripIn, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    if db.query(Trip).filter_by(tourist_code=p.subject, status="ACTIVE").first():
        raise HTTPException(409, "You already have an active trip. End it first.")
    trip = Trip(tourist_code=p.subject, title=data.title, destination=data.destination,
                planned_end_at=data.planned_end_at)
    db.add(trip)
    audit(db, "TRIP_STARTED", "TOURIST", p.subject)
    db.commit()
    db.refresh(trip)
    return trip_dict(trip)


@router.post("/trips/{trip_id}/end")
def end_trip(trip_id: int, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if trip is None or trip.tourist_code != p.subject:
        raise HTTPException(404, "Trip not found")
    if trip.status != "ACTIVE":
        raise HTTPException(409, "Trip is not active")
    trip.status = "COMPLETED"
    trip.ended_at = utc_now()
    audit(db, "TRIP_ENDED", "TOURIST", p.subject)
    db.commit()
    return trip_dict(trip)


# ----------------------------------------------------------- notifications
@router.get("/notifications")
def my_notifications(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter_by(recipient_type="TOURIST", recipient_id=p.subject, channel="IN_APP")
        .order_by(Notification.id.desc()).limit(100).all()
    )
    return [
        {"id": n.id, "category": n.category, "title": n.title, "body": n.body, "created_at": n.created_at,
         "read_at": n.read_at, "related_sos_id": n.related_sos_id}
        for n in rows
    ]


@router.post("/notifications/{note_id}/read")
def read_notification(note_id: int, p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    n = db.get(Notification, note_id)
    if n is None or n.recipient_type != "TOURIST" or n.recipient_id != p.subject:
        raise HTTPException(404, "Notification not found")
    n.read_at = n.read_at or utc_now()
    db.commit()
    return {"id": n.id, "read_at": n.read_at}


# ------------------------------------------------------------ safety report
@router.get("/safety-report")
def my_safety_report(p: Principal = Depends(require_tourist), db: Session = Depends(get_db)):
    since = utc_now() - timedelta(hours=24)
    points = [
        intelligence.Point(r.latitude, r.longitude, as_utc(r.recorded_at), r.accuracy)
        for r in db.query(LocationPoint).filter(LocationPoint.tourist_code == p.subject,
                                                LocationPoint.recorded_at >= since).all()
    ]
    events = [
        {"event_type": e.event_type, "zone_id": e.zone_id, "zone_name": e.zone_name, "zone_type": e.zone_type,
         "created_at": as_utc(e.created_at)}
        for e in db.query(GeofenceEvent).filter(GeofenceEvent.tourist_code == p.subject,
                                                GeofenceEvent.created_at >= since).all()
    ]
    open_sos = db.query(SOSAlert).filter(SOSAlert.tourist_code == p.subject,
                                         SOSAlert.status.in_(ACTIVE_SOS_STATUSES)).count()
    report = intelligence.assess_tourist(points, events, open_sos=open_sos)
    report["recent_geofence_events"] = sorted(events, key=lambda e: e["created_at"], reverse=True)[:20]
    return report
