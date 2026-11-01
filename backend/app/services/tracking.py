"""Location ingestion + geofence transitions (shared by legacy and v1 routes)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import as_utc, utc_now
from app.models.models import GeofenceEvent, LocationPoint, SafetyZone, SOSAlert, Tourist
from app.services import notifications
from app.services.geofence import ZoneShape, evaluate, transitions
from app.services.realtime import manager

ACTIVE_SOS_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESPONDING")


def active_zone_shapes(db: Session) -> list[ZoneShape]:
    return [ZoneShape.from_row(z) for z in db.query(SafetyZone).filter_by(active=True).all()]


def has_active_sos(db: Session, tourist_code: str) -> bool:
    return (
        db.query(SOSAlert.id)
        .filter(SOSAlert.tourist_code == tourist_code, SOSAlert.status.in_(ACTIVE_SOS_STATUSES))
        .first()
        is not None
    )


def previous_inside_zone_ids(db: Session, tourist_code: str) -> set[int]:
    """Zones the tourist is currently inside according to the event log."""
    inside: dict[int, str] = {}
    events = (
        db.query(GeofenceEvent)
        .filter_by(tourist_code=tourist_code)
        .order_by(GeofenceEvent.created_at.desc(), GeofenceEvent.id.desc())
        .limit(500)
        .all()
    )
    for event in events:  # newest first: first event per zone wins
        inside.setdefault(event.zone_id, event.event_type)
    return {zone_id for zone_id, kind in inside.items() if kind == "ENTER"}


def ingest_location(
    db: Session,
    tourist: Tourist,
    latitude: float,
    longitude: float,
    accuracy: float | None = None,
    speed: float | None = None,
    recorded_at: datetime | None = None,
    client_id: str | None = None,
) -> dict:
    settings = get_settings()
    now = utc_now()
    recorded_at = as_utc(recorded_at) or now
    if recorded_at > now + timedelta(minutes=5):
        recorded_at = now  # do not trust clocks far in the future

    if client_id:
        duplicate = db.query(LocationPoint).filter_by(tourist_code=tourist.tourist_code, client_id=client_id).first()
        if duplicate:
            return {"duplicate": True, "safety_status": tourist.safety_status, "restricted_zone_alerts": [],
                    "geofence_events": [], "nearby_zones": [], "nearest_restricted": None}

    result = evaluate(latitude, longitude, active_zone_shapes(db), settings.caution_buffer_ratio)
    is_latest = tourist.last_location_update is None or recorded_at >= as_utc(tourist.last_location_update)

    db.add(LocationPoint(
        tourist_code=tourist.tourist_code, latitude=latitude, longitude=longitude, accuracy=accuracy,
        speed=speed, safety_status=result.status, recorded_at=recorded_at, received_at=now, client_id=client_id,
    ))

    events = []
    if is_latest:
        tourist.latitude = latitude
        tourist.longitude = longitude
        tourist.location_accuracy = accuracy
        tourist.last_location_update = recorded_at
        status = "SOS" if has_active_sos(db, tourist.tourist_code) else result.status
        tourist.safety_status = status

        previous = previous_inside_zone_ids(db, tourist.tourist_code)
        entered, exited = transitions(previous, result.inside_ids)
        zone_lookup = {z["zone_id"]: z for z in result.inside}
        names = {}
        if exited:
            names = {z.id: z for z in db.query(SafetyZone).filter(SafetyZone.id.in_(exited)).all()}
        for zone_id in sorted(entered):
            z = zone_lookup[zone_id]
            events.append({"event_type": "ENTER", "zone_id": zone_id, "zone_name": z["zone_name"], "zone_type": z["zone_type"]})
        for zone_id in sorted(exited):
            z = names.get(zone_id)
            events.append({"event_type": "EXIT", "zone_id": zone_id,
                           "zone_name": z.name if z else None, "zone_type": z.zone_type if z else None})
        for e in events:
            db.add(GeofenceEvent(tourist_code=tourist.tourist_code, latitude=latitude, longitude=longitude,
                                 created_at=recorded_at, **e))
            if e["event_type"] == "ENTER" and e["zone_type"] in {"RESTRICTED", "HIGH_RISK"}:
                notifications.notify_tourist(
                    db, tourist, "RESTRICTED_ZONE_ENTRY", "Restricted zone warning",
                    f"You have entered {e['zone_name']}. Leave the area if it is safe to do so.",
                )
                notifications.notify_staff(
                    db, "RESTRICTED_ZONE_ENTRY", "Tourist entered a restricted zone",
                    f"{tourist.tourist_code} entered {e['zone_name']}.", roles={"SUPER_ADMIN", "ADMIN"},
                )
    db.commit()

    payload = {
        "tourist_code": tourist.tourist_code,
        "name": tourist.name,
        "latitude": tourist.latitude,
        "longitude": tourist.longitude,
        "accuracy": tourist.location_accuracy,
        "safety_status": tourist.safety_status,
        "last_location_update": tourist.last_location_update,
    }
    if is_latest:
        manager.publish("location.updated", payload)
        for e in events:
            manager.publish("geofence.event", {"tourist_code": tourist.tourist_code, **e})

    return {
        "duplicate": False,
        "safety_status": tourist.safety_status,
        "zone_status": result.status,
        "restricted_zone_alerts": [z for z in result.inside if z["zone_type"] in {"RESTRICTED", "HIGH_RISK"}],
        "inside_zones": result.inside,
        "nearby_zones": result.nearby,
        "nearest_restricted": result.nearest,
        "geofence_events": events,
        "is_latest": is_latest,
    }
