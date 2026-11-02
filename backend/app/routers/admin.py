"""Staff-facing management API: tourists, access list, staff, audit, data."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import ADMIN_ROLES, STAFF_ROLES, as_utc, hash_password, normalize_email, password_problems, utc_now
from app.database import get_db
from app.deps import Principal, require_admin, require_staff
from app.migrations import current_version, table_counts
from app.models.models import (
    AuditLog,
    GeofenceEvent,
    LocationPoint,
    SafetyZone,
    SOSAlert,
    StaffUser,
    Tourist,
    Trip,
)
from app.models.tourist_access import TouristAccess
from app.services import intelligence
from app.services import sos as sos_service
from app.services.audit import audit
from app.services.geodata import audit_zones
from app.services.tracking import ACTIVE_SOS_STATUSES

router = APIRouter(prefix="/api/v1/admin", tags=["administration"])


# ----------------------------------------------------------------- helpers
def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    return f"{local[:2]}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    return "*" * max(0, len(value) - 3) + value[-3:]


def tourist_row(t: Tourist, principal: Principal, contact_visible: bool = False) -> dict:
    full = principal.is_admin or contact_visible
    settings = get_settings()
    stale = None
    if t.last_location_update:
        stale = (utc_now() - as_utc(t.last_location_update)).total_seconds() / 60 > settings.stale_location_minutes
    return {
        "tourist_code": t.tourist_code,
        "name": t.name,
        "phone": t.phone if full else mask_phone(t.phone),
        "college_email": t.college_email if full else mask_email(t.college_email),
        "enrollment_number": t.enrollment_number if principal.is_admin else None,
        "emergency_contact_name": t.emergency_contact_name if full else None,
        "emergency_contact_phone": t.emergency_contact_phone if full else mask_phone(t.emergency_contact_phone),
        "emergency_contact_email": t.emergency_contact_email if full else mask_email(t.emergency_contact_email),
        "latitude": t.latitude,
        "longitude": t.longitude,
        "location_accuracy": t.location_accuracy,
        "safety_status": t.safety_status,
        "last_location_update": t.last_location_update,
        "location_stale": stale,
        "consent_given": t.location_consent_at is not None,
        "created_at": t.created_at,
    }


def police_can_see_contact(db: Session, principal: Principal, tourist_code: str) -> bool:
    """Police see full contact details only while handling an active SOS."""
    if principal.is_admin:
        return True
    q = db.query(SOSAlert.id).filter(SOSAlert.tourist_code == tourist_code, SOSAlert.status.in_(ACTIVE_SOS_STATUSES))
    return q.filter(or_(SOSAlert.assigned_officer_id == principal.staff.id,
                        SOSAlert.assigned_officer_id.is_(None))).first() is not None


SORTS = {
    "name": Tourist.name,
    "code": Tourist.tourist_code,
    "status": Tourist.safety_status,
    "last_seen": Tourist.last_location_update,
    "created": Tourist.created_at,
}


# --------------------------------------------------------------- tourists
@router.get("/tourists")
def list_tourists(
    search: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=20),
    active_only: bool = False,
    sort: str = Query(default="last_seen"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    q = db.query(Tourist)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(Tourist.tourist_code.ilike(like), Tourist.name.ilike(like)))
    if status:
        q = q.filter(Tourist.safety_status == status.upper())
    if active_only:
        cutoff = utc_now() - timedelta(minutes=get_settings().stale_location_minutes)
        q = q.filter(Tourist.last_location_update >= cutoff)
    total = q.count()
    column = SORTS.get(sort, Tourist.last_location_update)
    q = q.order_by(column.desc() if order == "desc" else column.asc(), Tourist.id.desc())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [tourist_row(t, principal, police_can_see_contact(db, principal, t.tourist_code)) for t in rows],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/tourists/{tourist_code}")
def tourist_detail(tourist_code: str, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    t = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if t is None:
        raise HTTPException(404, "Tourist not found")
    visible = police_can_see_contact(db, principal, tourist_code)
    audit(db, "TOURIST_VIEWED", "STAFF", principal.subject, f"tourist:{tourist_code}", commit=True)
    alerts = db.query(SOSAlert).filter_by(tourist_code=tourist_code).order_by(SOSAlert.id.desc()).limit(20).all()
    trips = db.query(Trip).filter_by(tourist_code=tourist_code).order_by(Trip.id.desc()).limit(10).all()
    events = (
        db.query(GeofenceEvent).filter_by(tourist_code=tourist_code)
        .order_by(GeofenceEvent.created_at.desc()).limit(30).all()
    )
    since = utc_now() - timedelta(hours=24)
    points = [
        intelligence.Point(r.latitude, r.longitude, as_utc(r.recorded_at), r.accuracy)
        for r in db.query(LocationPoint).filter(LocationPoint.tourist_code == tourist_code,
                                                LocationPoint.recorded_at >= since).all()
    ]
    event_dicts = [
        {"event_type": e.event_type, "zone_id": e.zone_id, "zone_name": e.zone_name, "zone_type": e.zone_type,
         "created_at": as_utc(e.created_at)}
        for e in events
    ]
    open_sos = sum(1 for a in alerts if a.status in ACTIVE_SOS_STATUSES)
    return {
        "tourist": tourist_row(t, principal, visible),
        "contact_visible": visible,
        "alerts": [sos_service.serialize(a, db) for a in alerts],
        "trips": [{"id": tr.id, "title": tr.title, "destination": tr.destination, "status": tr.status,
                   "started_at": tr.started_at, "ended_at": tr.ended_at} for tr in trips],
        "geofence_events": [{**e, "created_at": e["created_at"]} for e in event_dicts],
        "assessment": intelligence.assess_tourist(points, event_dicts, open_sos=open_sos),
    }


@router.get("/tourists/{tourist_code}/locations")
def tourist_locations(
    tourist_code: str,
    hours: int = Query(default=24, ge=1, le=24 * 30),
    principal: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if not principal.is_admin and not police_can_see_contact(db, principal, tourist_code):
        raise HTTPException(403, "Location history is available to officers only during an active SOS")
    since = utc_now() - timedelta(hours=hours)
    rows = (
        db.query(LocationPoint)
        .filter(LocationPoint.tourist_code == tourist_code, LocationPoint.recorded_at >= since)
        .order_by(LocationPoint.recorded_at.asc()).limit(5000).all()
    )
    audit(db, "LOCATION_HISTORY_VIEWED", "STAFF", principal.subject, f"tourist:{tourist_code}",
          {"hours": hours}, commit=True)
    return [
        {"latitude": r.latitude, "longitude": r.longitude, "accuracy": r.accuracy,
         "safety_status": r.safety_status, "recorded_at": r.recorded_at}
        for r in rows
    ]


class TouristCreate(BaseModel):
    tourist_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    enrollment_number: str | None = Field(default=None, max_length=50)
    college_email: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    emergency_contact_email: str | None = Field(default=None, max_length=255)
    login_gmail: str | None = Field(default=None, max_length=255)


@router.post("/tourists", status_code=201)
def create_tourist(data: TouristCreate, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Tourist).filter_by(tourist_code=data.tourist_code).first():
        raise HTTPException(409, "Tourist code already exists")
    fields = data.model_dump(exclude={"login_gmail"})
    t = Tourist(**fields)
    db.add(t)
    if data.login_gmail:
        _add_access(db, data.login_gmail, data.tourist_code)
    audit(db, "TOURIST_CREATED", "STAFF", principal.subject, f"tourist:{data.tourist_code}")
    db.commit()
    return tourist_row(t, principal)


class TouristPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    enrollment_number: str | None = Field(default=None, max_length=50)
    college_email: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=20)
    emergency_contact_email: str | None = Field(default=None, max_length=255)


@router.patch("/tourists/{tourist_code}")
def update_tourist(tourist_code: str, data: TouristPatch, principal: Principal = Depends(require_admin),
                   db: Session = Depends(get_db)):
    t = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if t is None:
        raise HTTPException(404, "Tourist not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(t, key, value if key == "name" else (value or None))
    audit(db, "TOURIST_UPDATED", "STAFF", principal.subject, f"tourist:{tourist_code}", {"fields": sorted(changes)})
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Enrollment number or college email already belongs to another tourist")
    return tourist_row(t, principal)


@router.delete("/tourists/{tourist_code}")
def delete_tourist(
    tourist_code: str,
    confirm: str = Query(..., description="Must equal the tourist code"),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Super admin only. Removes the profile, login access, location history,
    trips and geofence events. SOS records are kept for the incident audit trail."""
    if principal.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only a super admin can delete tourist records")
    if confirm != tourist_code:
        raise HTTPException(409, "confirm must equal the tourist code")
    t = db.query(Tourist).filter_by(tourist_code=tourist_code).first()
    if t is None:
        raise HTTPException(404, "Tourist not found")
    if db.query(SOSAlert.id).filter(SOSAlert.tourist_code == tourist_code, SOSAlert.status.in_(ACTIVE_SOS_STATUSES)).first():
        raise HTTPException(409, "Resolve the tourist's active SOS before deleting the record")
    counts = {
        "locations": db.query(LocationPoint).filter_by(tourist_code=tourist_code).delete(),
        "geofence_events": db.query(GeofenceEvent).filter_by(tourist_code=tourist_code).delete(),
        "trips": db.query(Trip).filter_by(tourist_code=tourist_code).delete(),
        "access": db.query(TouristAccess).filter_by(tourist_code=tourist_code).delete(),
    }
    db.delete(t)
    audit(db, "TOURIST_DELETED", "STAFF", principal.subject, f"tourist:{tourist_code}", counts)
    db.commit()
    return {"deleted": True, "tourist_code": tourist_code, **counts}


# ------------------------------------------------------- tourist access list
class AccessCreate(BaseModel):
    email: str = Field(min_length=6, max_length=255)
    tourist_code: str = Field(min_length=2, max_length=50)


class AccessUpdate(BaseModel):
    active: bool


def _add_access(db: Session, email: str, tourist_code: str) -> TouristAccess:
    email = email.strip().lower()
    domain = email.rpartition("@")[2]
    if domain not in get_settings().tourist_email_domains:
        raise HTTPException(422, "Tourist login must be a Gmail address")
    wanted = normalize_email(email)
    for row in db.query(TouristAccess).all():
        if normalize_email(row.email) == wanted:
            raise HTTPException(409, "This Gmail address is already linked to a tourist")
        if row.tourist_code == tourist_code:
            raise HTTPException(409, "This tourist already has a login email")
    row = TouristAccess(email=email, tourist_code=tourist_code, active=True)
    db.add(row)
    return row


@router.get("/tourist-access")
def list_access(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    names = {t.tourist_code: t.name for t in db.query(Tourist).all()}
    return [
        {"id": a.id, "email": a.email, "tourist_code": a.tourist_code, "active": a.active,
         "tourist_name": names.get(a.tourist_code), "tourist_exists": a.tourist_code in names}
        for a in db.query(TouristAccess).order_by(TouristAccess.id).all()
    ]


@router.post("/tourist-access", status_code=201)
def create_access(data: AccessCreate, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.query(Tourist).filter_by(tourist_code=data.tourist_code).first():
        raise HTTPException(404, "Tourist not found")
    row = _add_access(db, data.email, data.tourist_code)
    audit(db, "TOURIST_ACCESS_GRANTED", "STAFF", principal.subject, f"tourist:{data.tourist_code}")
    db.commit()
    return {"id": row.id, "email": row.email, "tourist_code": row.tourist_code, "active": row.active}


@router.delete("/tourist-access/{access_id}")
def delete_access(access_id: int, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(TouristAccess, access_id)
    if row is None:
        raise HTTPException(404, "Access record not found")
    audit(db, "TOURIST_ACCESS_REMOVED", "STAFF", principal.subject, f"tourist:{row.tourist_code}")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": access_id}


@router.patch("/tourist-access/{access_id}")
def update_access(access_id: int, data: AccessUpdate, principal: Principal = Depends(require_admin),
                  db: Session = Depends(get_db)):
    row = db.get(TouristAccess, access_id)
    if row is None:
        raise HTTPException(404, "Access record not found")
    row.active = data.active
    audit(db, "TOURIST_ACCESS_" + ("ENABLED" if data.active else "DISABLED"), "STAFF", principal.subject,
          f"tourist:{row.tourist_code}")
    db.commit()
    return {"id": row.id, "active": row.active}


# ------------------------------------------------------------------- staff
class StaffCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(SUPER_ADMIN|ADMIN|POLICE)$")
    password: str = Field(min_length=10, max_length=200)
    badge_number: str | None = Field(default=None, max_length=50)
    station: str | None = Field(default=None, max_length=120)


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    active: bool | None = None
    role: str | None = Field(default=None, pattern="^(SUPER_ADMIN|ADMIN|POLICE)$")
    password: str | None = Field(default=None, min_length=10, max_length=200)
    badge_number: str | None = Field(default=None, max_length=50)
    station: str | None = Field(default=None, max_length=120)


def staff_dict(u: StaffUser) -> dict:
    return {
        "id": u.id, "email": u.email, "name": u.name, "role": u.role, "active": u.active,
        "badge_number": u.badge_number, "station": u.station, "last_login_at": u.last_login_at,
        "locked": bool(u.locked_until and as_utc(u.locked_until) > utc_now()), "created_at": u.created_at,
    }


@router.get("/staff")
def list_staff(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    return [staff_dict(u) for u in db.query(StaffUser).order_by(StaffUser.role, StaffUser.name).all()]


@router.post("/staff", status_code=201)
def create_staff(data: StaffCreate, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if data.role in ADMIN_ROLES and principal.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only a super admin can create admin accounts")
    problems = password_problems(data.password)
    if problems:
        raise HTTPException(422, "Password needs " + ", ".join(problems))
    email = data.email.strip().lower()
    if db.query(StaffUser).filter_by(email=email).first():
        raise HTTPException(409, "A staff account with this email already exists")
    user = StaffUser(email=email, name=data.name, role=data.role, password_hash=hash_password(data.password),
                     badge_number=data.badge_number, station=data.station)
    db.add(user)
    db.flush()
    audit(db, "STAFF_CREATED", "STAFF", principal.subject, f"staff:{user.id}", {"role": data.role})
    db.commit()
    return staff_dict(user)


@router.patch("/staff/{staff_id}")
def update_staff(staff_id: int, data: StaffUpdate, principal: Principal = Depends(require_admin),
                 db: Session = Depends(get_db)):
    user = db.get(StaffUser, staff_id)
    if user is None:
        raise HTTPException(404, "Staff account not found")
    touches_admin = user.role in ADMIN_ROLES or (data.role in ADMIN_ROLES if data.role else False)
    if touches_admin and principal.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only a super admin can change admin accounts")
    if user.id == principal.staff.id and (data.active is False or (data.role and data.role != user.role)):
        raise HTTPException(409, "You cannot deactivate or demote your own account")
    changes = data.model_dump(exclude_unset=True)
    if "password" in changes:
        problems = password_problems(changes["password"])
        if problems:
            raise HTTPException(422, "Password needs " + ", ".join(problems))
        user.password_hash = hash_password(changes.pop("password"))
        user.locked_until = None
        user.failed_attempts = 0
    for key, value in changes.items():
        setattr(user, key, value)
    audit(db, "STAFF_UPDATED", "STAFF", principal.subject, f"staff:{user.id}", {"fields": sorted(data.model_dump(exclude_unset=True))})
    db.commit()
    return staff_dict(user)


@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: int, principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(StaffUser, staff_id)
    if user is None:
        raise HTTPException(404, "Staff account not found")
    if user.role in ADMIN_ROLES and principal.role != "SUPER_ADMIN":
        raise HTTPException(403, "Only a super admin can delete admin accounts")
    if user.id == principal.staff.id:
        raise HTTPException(409, "You cannot delete your own account")
    if db.query(SOSAlert.id).filter(SOSAlert.assigned_officer_id == user.id, SOSAlert.status.in_(ACTIVE_SOS_STATUSES)).first():
        raise HTTPException(409, "Reassign this officer's active incidents first")
    audit(db, "STAFF_DELETED", "STAFF", principal.subject, f"staff:{user.id}", {"role": user.role})
    db.delete(user)
    db.commit()
    return {"deleted": True, "id": staff_id}


@router.get("/officers")
def list_officers(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    """Police officers available for assignment (any staff may view)."""
    users = db.query(StaffUser).filter(StaffUser.role == "POLICE", StaffUser.active.is_(True)).order_by(StaffUser.name).all()
    open_counts = {}
    for a in db.query(SOSAlert).filter(SOSAlert.status.in_(ACTIVE_SOS_STATUSES), SOSAlert.assigned_officer_id.isnot(None)).all():
        open_counts[a.assigned_officer_id] = open_counts.get(a.assigned_officer_id, 0) + 1
    return [{"id": u.id, "name": u.name, "badge_number": u.badge_number, "station": u.station,
             "active_incidents": open_counts.get(u.id, 0)} for u in users]


# -------------------------------------------------------------- audit/data
@router.get("/audit-logs")
def audit_logs(
    action: str | None = Query(default=None, max_length=60),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    total = q.count()
    rows = q.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [{"id": r.id, "actor_type": r.actor_type, "actor_id": r.actor_id, "action": r.action,
                   "target": r.target, "detail": r.detail, "ip_address": r.ip_address, "created_at": r.created_at}
                  for r in rows],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/data-audit")
def data_audit(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    """Read-only integrity report. Contains no personal data."""
    from app.database import engine

    zones = db.query(SafetyZone).all()
    tourists = db.query(Tourist).all()
    access = db.query(TouristAccess).all()
    codes = {t.tourist_code for t in tourists}
    invalid_tourist_coords = sum(
        1 for t in tourists
        if t.latitude is not None and not (-90 <= t.latitude <= 90 and -180 <= (t.longitude or 0) <= 180)
    )
    return {
        "schema_version": current_version(engine),
        "table_counts": table_counts(engine),
        "tourists": {
            "total": len(tourists),
            "with_login_access": sum(1 for a in access if a.active and a.tourist_code in codes),
            "access_rows_without_tourist": sum(1 for a in access if a.tourist_code not in codes),
            "access_emails_gmail": sum(1 for a in access if a.email.lower().endswith(("@gmail.com", "@googlemail.com"))),
            "invalid_coordinates": invalid_tourist_coords,
        },
        "sos": {"total": db.query(SOSAlert).count(),
                "orphaned": sum(1 for a in db.query(SOSAlert).all() if a.tourist_code not in codes)},
        "zones": audit_zones(zones),
    }


@router.post("/retention/purge")
def purge_old_locations(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    days = get_settings().location_retention_days
    cutoff = utc_now() - timedelta(days=days)
    count = db.query(LocationPoint).filter(LocationPoint.recorded_at < cutoff).delete()
    audit(db, "LOCATION_RETENTION_PURGE", "STAFF", principal.subject, None, {"rows": count, "days": days})
    db.commit()
    return {"deleted": count, "retention_days": days}


__all__ = ["router", "STAFF_ROLES"]
