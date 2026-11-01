"""SOS incident lifecycle.

OPEN -> ACKNOWLEDGED -> RESPONDING -> RESOLVED
Any active state can also go to RESOLVED (with an outcome) and OPEN can be
CANCELLED by the tourist. Resolution always needs a human actor and notes.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.models import IncidentEvent, SOSAlert, StaffUser, Tourist
from app.services import notifications
from app.services.audit import audit
from app.services.realtime import manager

STATUSES = ("OPEN", "ACKNOWLEDGED", "RESPONDING", "RESOLVED", "CANCELLED")
ACTIVE = ("OPEN", "ACKNOWLEDGED", "RESPONDING")
ALERT_TYPES = ("GENERAL", "MEDICAL", "CRIME", "ACCIDENT", "LOST", "HARASSMENT", "OTHER")
OUTCOMES = ("ASSISTED", "FALSE_ALARM", "REFERRED", "UNREACHABLE", "OTHER")
TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "RESPONDING", "RESOLVED", "CANCELLED"},
    "ACKNOWLEDGED": {"RESPONDING", "RESOLVED"},
    "RESPONDING": {"RESOLVED"},
    "RESOLVED": set(),
    "CANCELLED": set(),
}
TOURIST_MESSAGES = {
    "ACKNOWLEDGED": ("SOS acknowledged", "Your SOS has been acknowledged by the monitoring team."),
    "RESPONDING": ("Help is on the way", "An officer is responding to your SOS."),
    "RESOLVED": ("SOS resolved", "Your SOS incident has been marked resolved."),
    "CANCELLED": ("SOS cancelled", "Your SOS was cancelled."),
}


def serialize(alert: SOSAlert, db: Session | None = None, include_events: bool = False,
              tourist: Tourist | None = None, officer: StaffUser | None = None) -> dict:
    data = {
        "id": alert.id,
        "tourist_code": alert.tourist_code,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "accuracy": alert.accuracy,
        "message": alert.message,
        "alert_type": alert.alert_type or "GENERAL",
        "status": alert.status,
        "assigned_officer_id": alert.assigned_officer_id,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "resolved_at": alert.resolved_at,
        "resolution_outcome": alert.resolution_outcome,
        "resolution_notes": alert.resolution_notes,
        "updated_at": alert.updated_at,
    }
    if db is not None:
        tourist = tourist or db.query(Tourist).filter_by(tourist_code=alert.tourist_code).first()
        if alert.assigned_officer_id and officer is None:
            officer = db.get(StaffUser, alert.assigned_officer_id)
    if tourist is not None:
        data["tourist_name"] = tourist.name
    if officer is not None:
        data["assigned_officer"] = {"id": officer.id, "name": officer.name, "badge_number": officer.badge_number}
    if include_events and db is not None:
        events = db.query(IncidentEvent).filter_by(sos_id=alert.id).order_by(IncidentEvent.created_at, IncidentEvent.id).all()
        data["timeline"] = [
            {
                "id": e.id, "action": e.action, "actor_type": e.actor_type, "actor_name": e.actor_name,
                "from_status": e.from_status, "to_status": e.to_status, "note": e.note, "created_at": e.created_at,
            }
            for e in events
        ]
    return data


def create_alert(
    db: Session,
    tourist: Tourist,
    latitude: float | None,
    longitude: float | None,
    message: str | None,
    accuracy: float | None = None,
    alert_type: str = "GENERAL",
    idempotency_key: str | None = None,
    actor_type: str = "TOURIST",
    actor_id: str | None = None,
) -> tuple[SOSAlert, bool]:
    """Returns (alert, created). Repeated idempotency keys return the original."""
    if idempotency_key:
        existing = db.query(SOSAlert).filter_by(tourist_code=tourist.tourist_code, idempotency_key=idempotency_key).first()
        if existing:
            return existing, False

    if latitude is None or longitude is None:
        latitude, longitude = tourist.latitude, tourist.longitude
    alert = SOSAlert(
        tourist_code=tourist.tourist_code,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        message=message or "Emergency assistance required",
        alert_type=alert_type if alert_type in ALERT_TYPES else "OTHER",
        idempotency_key=idempotency_key,
        status="OPEN",
    )
    tourist.safety_status = "SOS"
    db.add(alert)
    db.flush()
    db.add(IncidentEvent(
        sos_id=alert.id, actor_type=actor_type, actor_id=actor_id or tourist.tourist_code,
        actor_name=tourist.name, action="CREATED", to_status="OPEN", note=alert.message,
    ))
    audit(db, "SOS_CREATED", actor_type, actor_id or tourist.tourist_code, f"sos:{alert.id}")
    return alert, True


def notify_new_alert(db: Session, tourist: Tourist, alert: SOSAlert) -> list[dict]:
    location = (
        f"{alert.latitude:.6f}, {alert.longitude:.6f}" if alert.latitude is not None and alert.longitude is not None
        else "unavailable"
    )
    body = (
        f"Tourist {tourist.name} ({tourist.tourist_code}) triggered SOS #{alert.id}. "
        f"Type: {alert.alert_type}. Location: {location}. Message: {alert.message}"
    )
    results = notifications.notify_staff(
        db, "SOS_ALERT", f"SOS #{alert.id}: {tourist.name}", body,
        dedupe_key=f"sos:{alert.id}:created", related_sos_id=alert.id, email_admin=True,
    )
    results.append(notifications.notify_contact_email(db, tourist, f"SOS ALERT: {tourist.name}", body, alert.id))
    results += notifications.notify_tourist(
        db, tourist, "SOS_ALERT", "SOS received",
        f"Your SOS #{alert.id} was recorded by the server. The monitoring team has been alerted.",
        dedupe_key=f"sos:{alert.id}:received", related_sos_id=alert.id,
    )
    return results


def publish(db: Session, alert: SOSAlert, event: str) -> None:
    data = serialize(alert, db)
    manager.publish(event, data, staff=True, tourist_code=alert.tourist_code)


def transition(
    db: Session,
    alert: SOSAlert,
    to_status: str,
    actor_type: str,
    actor_id: str,
    actor_name: str,
    note: str | None = None,
    action: str | None = None,
) -> SOSAlert:
    to_status = to_status.upper()
    if to_status not in STATUSES:
        raise HTTPException(422, f"status must be one of {', '.join(STATUSES)}")
    if to_status not in TRANSITIONS.get(alert.status, set()):
        raise HTTPException(409, f"Cannot move SOS from {alert.status} to {to_status}")
    previous = alert.status
    alert.status = to_status
    now = utc_now()
    if to_status == "ACKNOWLEDGED" or (to_status in {"RESPONDING", "RESOLVED"} and not alert.acknowledged_at):
        alert.acknowledged_at = alert.acknowledged_at or now
    if to_status in {"RESOLVED", "CANCELLED"}:
        alert.resolved_at = now
    db.add(IncidentEvent(
        sos_id=alert.id, actor_type=actor_type, actor_id=actor_id, actor_name=actor_name,
        action=action or to_status, from_status=previous, to_status=to_status, note=note,
    ))
    audit(db, f"SOS_{to_status}", actor_type, actor_id, f"sos:{alert.id}", {"from": previous})

    tourist = db.query(Tourist).filter_by(tourist_code=alert.tourist_code).first()
    if tourist is not None:
        title, body = TOURIST_MESSAGES[to_status]
        category = "SOS_ACKNOWLEDGED" if to_status == "ACKNOWLEDGED" else "EMERGENCY_RESPONSE"
        notifications.notify_tourist(
            db, tourist, category, title, body + (f" Note: {note}" if note and to_status != "CANCELLED" else ""),
            dedupe_key=f"sos:{alert.id}:{to_status}", related_sos_id=alert.id,
        )
        if to_status in {"RESOLVED", "CANCELLED"}:
            still_active = (
                db.query(SOSAlert.id)
                .filter(SOSAlert.tourist_code == tourist.tourist_code, SOSAlert.status.in_(ACTIVE), SOSAlert.id != alert.id)
                .first()
            )
            if not still_active and tourist.safety_status == "SOS":
                # Re-derive the status from the last known position instead of
                # assuming the tourist is safe.
                from app.services.geofence import evaluate
                from app.services.tracking import active_zone_shapes

                if tourist.latitude is None or tourist.longitude is None:
                    tourist.safety_status = "UNKNOWN"
                else:
                    tourist.safety_status = evaluate(tourist.latitude, tourist.longitude, active_zone_shapes(db)).status
    db.commit()
    db.refresh(alert)
    publish(db, alert, "sos.updated")
    return alert
