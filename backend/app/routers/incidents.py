"""SOS command centre for admins and police officers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import Principal, require_staff
from app.models.models import IncidentEvent, SOSAlert, StaffUser
from app.services import sos as sos_service
from app.services.audit import audit
from app.services.geofence import distance_meters

router = APIRouter(prefix="/api/v1/sos", tags=["sos incidents"])


class AssignIn(BaseModel):
    officer_id: int
    note: str | None = Field(default=None, max_length=1000)


class StatusIn(BaseModel):
    status: str = Field(max_length=20)
    note: str | None = Field(default=None, max_length=1000)


class ResolveIn(BaseModel):
    outcome: str = Field(max_length=40)
    notes: str = Field(min_length=3, max_length=2000)


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


def _get(db: Session, alert_id: int, principal: Principal) -> SOSAlert:
    alert = db.get(SOSAlert, alert_id)
    if alert is None:
        raise HTTPException(404, "SOS alert not found")
    if principal.role == "POLICE" and alert.assigned_officer_id not in (None, principal.staff.id):
        raise HTTPException(403, "This incident is assigned to another officer")
    return alert


@router.get("")
def list_alerts(
    status: str | None = Query(default=None, max_length=20),
    scope: str = Query(default="all", pattern="^(all|mine|active)$"),
    near_lat: float | None = Query(default=None, ge=-90, le=90),
    near_lon: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=100, ge=1, le=500),
    principal: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    q = db.query(SOSAlert)
    if principal.role == "POLICE":
        # Officers see unassigned alerts and their own; never other officers' cases.
        q = q.filter(or_(SOSAlert.assigned_officer_id.is_(None), SOSAlert.assigned_officer_id == principal.staff.id))
    if scope == "mine":
        q = q.filter(SOSAlert.assigned_officer_id == principal.staff.id)
    elif scope == "active":
        q = q.filter(SOSAlert.status.in_(sos_service.ACTIVE))
    if status:
        q = q.filter(SOSAlert.status == status.upper())
    rows = q.order_by(SOSAlert.id.desc()).limit(limit).all()
    officers = {u.id: u for u in db.query(StaffUser).filter(StaffUser.role == "POLICE").all()}
    out = []
    for a in rows:
        item = sos_service.serialize(a, db, officer=officers.get(a.assigned_officer_id))
        if near_lat is not None and near_lon is not None and a.latitude is not None:
            item["distance_meters"] = round(distance_meters(near_lat, near_lon, a.latitude, a.longitude), 1)
        out.append(item)
    if near_lat is not None and near_lon is not None:
        out.sort(key=lambda r: r.get("distance_meters", float("inf")))
    return out


@router.get("/{alert_id}")
def get_alert(alert_id: int, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    alert = _get(db, alert_id, principal)
    audit(db, "SOS_VIEWED", "STAFF", principal.subject, f"sos:{alert.id}", commit=True)
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/acknowledge")
def acknowledge(alert_id: int, body: NoteIn | None = None, principal: Principal = Depends(require_staff),
                db: Session = Depends(get_db)):
    alert = _get(db, alert_id, principal)
    alert = sos_service.transition(db, alert, "ACKNOWLEDGED", "STAFF", principal.subject, principal.name,
                                   body.note if body else None)
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/accept")
def accept(alert_id: int, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    """An officer takes the case: assigns themself and moves to RESPONDING."""
    if principal.role != "POLICE":
        raise HTTPException(403, "Only police officers can accept an incident; admins should assign one")
    alert = _get(db, alert_id, principal)
    if alert.status not in sos_service.ACTIVE:
        raise HTTPException(409, "Incident is no longer active")
    alert.assigned_officer_id = principal.staff.id
    db.add(IncidentEvent(sos_id=alert.id, actor_type="STAFF", actor_id=principal.subject, actor_name=principal.name,
                         action="ACCEPTED", note=f"Accepted by {principal.name}"))
    if alert.status == "RESPONDING":
        db.commit()
        sos_service.publish(db, alert, "sos.updated")
    else:
        alert = sos_service.transition(db, alert, "RESPONDING", "STAFF", principal.subject, principal.name,
                                       "Officer en route")
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/assign")
def assign(alert_id: int, data: AssignIn, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    if not principal.is_admin:
        raise HTTPException(403, "Only admins can assign incidents to officers")
    alert = _get(db, alert_id, principal)
    if alert.status not in sos_service.ACTIVE:
        raise HTTPException(409, "Incident is no longer active")
    officer = db.get(StaffUser, data.officer_id)
    if officer is None or officer.role != "POLICE" or not officer.active:
        raise HTTPException(422, "Officer not found or inactive")
    alert.assigned_officer_id = officer.id
    db.add(IncidentEvent(sos_id=alert.id, actor_type="STAFF", actor_id=principal.subject, actor_name=principal.name,
                         action="ASSIGNED", note=data.note or f"Assigned to {officer.name}"))
    audit(db, "SOS_ASSIGNED", "STAFF", principal.subject, f"sos:{alert.id}", {"officer_id": officer.id})
    from app.services import notifications

    notifications.notify_staff(db, "EMERGENCY_RESPONSE", f"SOS #{alert.id} assigned to you",
                               f"You have been assigned SOS #{alert.id}.", roles={"POLICE"},
                               dedupe_key=f"sos:{alert.id}:assign:{officer.id}", related_sos_id=alert.id)
    db.commit()
    db.refresh(alert)
    sos_service.publish(db, alert, "sos.updated")
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/status")
def set_status(alert_id: int, data: StatusIn, principal: Principal = Depends(require_staff),
               db: Session = Depends(get_db)):
    target = data.status.upper()
    if target == "RESOLVED":
        raise HTTPException(422, "Use /resolve with an outcome and notes to resolve an incident")
    if target == "CANCELLED":
        raise HTTPException(422, "Only the tourist can cancel an SOS; resolve it as FALSE_ALARM instead")
    alert = _get(db, alert_id, principal)
    alert = sos_service.transition(db, alert, target, "STAFF", principal.subject, principal.name, data.note)
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/resolve")
def resolve(alert_id: int, data: ResolveIn, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    outcome = data.outcome.upper()
    if outcome not in sos_service.OUTCOMES:
        raise HTTPException(422, f"outcome must be one of {', '.join(sos_service.OUTCOMES)}")
    alert = _get(db, alert_id, principal)
    if alert.status not in sos_service.ACTIVE:
        raise HTTPException(409, "Incident is not active")
    alert.resolution_outcome = outcome
    alert.resolution_notes = data.notes
    alert = sos_service.transition(db, alert, "RESOLVED", "STAFF", principal.subject, principal.name,
                                   f"{outcome}: {data.notes}")
    return sos_service.serialize(alert, db, include_events=True)


@router.post("/{alert_id}/notes")
def add_note(alert_id: int, data: NoteIn, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    alert = _get(db, alert_id, principal)
    db.add(IncidentEvent(sos_id=alert.id, actor_type="STAFF", actor_id=principal.subject, actor_name=principal.name,
                         action="NOTE", note=data.note))
    db.commit()
    sos_service.publish(db, alert, "sos.updated")
    return sos_service.serialize(alert, db, include_events=True)
