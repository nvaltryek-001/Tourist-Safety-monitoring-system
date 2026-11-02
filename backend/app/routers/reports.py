"""CSV reports for admins and monitoring metrics."""

from __future__ import annotations

import csv
import io
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import as_utc, utc_now
from app.database import get_db
from app.deps import Principal, require_admin
from app.models.models import AuditLog, GeofenceEvent, SafetyZone, SOSAlert, StaffUser, Tourist
from app.services import intelligence
from app.services.audit import audit

router = APIRouter(tags=["reports & monitoring"])
STARTED = time.time()
METRICS = {"requests": 0, "errors_5xx": 0, "errors_4xx": 0}


def _csv(name: str, header: list[str], rows) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/api/v1/reports/incidents.csv")
def incidents_report(days: int = Query(default=90, ge=1, le=3650), principal: Principal = Depends(require_admin),
                     db: Session = Depends(get_db)):
    since = utc_now() - timedelta(days=days)
    officers = {u.id: u.name for u in db.query(StaffUser).all()}
    rows = []
    for a in db.query(SOSAlert).filter(SOSAlert.created_at >= since).order_by(SOSAlert.id).all():
        created = as_utc(a.created_at)
        ack = round((as_utc(a.acknowledged_at) - created).total_seconds() / 60, 1) if a.acknowledged_at else None
        res = round((as_utc(a.resolved_at) - created).total_seconds() / 60, 1) if a.resolved_at else None
        rows.append([a.id, a.tourist_code, a.alert_type or "GENERAL", a.status, created.isoformat(),
                     a.latitude, a.longitude, officers.get(a.assigned_officer_id, ""), ack, res, a.resolution_outcome or ""])
    audit(db, "REPORT_EXPORTED", "STAFF", principal.subject, "incidents.csv", {"days": days, "rows": len(rows)}, commit=True)
    return _csv("safetrail_incidents.csv", ["sos_id", "tourist_code", "type", "status", "created_at", "latitude", "longitude",
                                            "assigned_officer", "minutes_to_ack", "minutes_to_resolve", "outcome"], rows)


@router.get("/api/v1/reports/zones.csv")
def zones_report(days: int = Query(default=30, ge=1, le=365), principal: Principal = Depends(require_admin),
                 db: Session = Depends(get_db)):
    since = utc_now() - timedelta(days=days)
    events = [{"tourist_code": e.tourist_code, "zone_id": e.zone_id, "zone_name": e.zone_name, "zone_type": e.zone_type,
               "event_type": e.event_type, "created_at": as_utc(e.created_at)}
              for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since).all()]
    activity = {r["zone_id"]: r for r in intelligence.zone_activity(events)}
    rows = []
    for z in db.query(SafetyZone).order_by(SafetyZone.id).all():
        a = activity.get(z.id, {})
        rows.append([z.id, z.name, z.zone_type, z.risk_level or "", z.active, z.verification_status or "", z.category or "",
                     z.radius_meters, z.latitude, z.longitude, a.get("entries", 0), a.get("unique_tourists", 0),
                     a.get("median_dwell_minutes")])
    audit(db, "REPORT_EXPORTED", "STAFF", principal.subject, "zones.csv", {"days": days}, commit=True)
    return _csv("safetrail_zones.csv", ["zone_id", "name", "type", "risk_level", "active", "verification", "category",
                                        "radius_m", "latitude", "longitude", f"entries_{days}d", "unique_tourists", "median_dwell_min"], rows)


@router.get("/api/v1/reports/tourists.csv")
def tourists_report(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    """Operational summary only — no phone numbers, emails or coordinates."""
    sos = {}
    for a in db.query(SOSAlert).all():
        sos[a.tourist_code] = sos.get(a.tourist_code, 0) + 1
    rows = [[t.tourist_code, t.name, t.safety_status, t.location_consent_at is not None,
             as_utc(t.last_location_update).isoformat() if t.last_location_update else "", sos.get(t.tourist_code, 0)]
            for t in db.query(Tourist).order_by(Tourist.tourist_code).all()]
    audit(db, "REPORT_EXPORTED", "STAFF", principal.subject, "tourists.csv", {"rows": len(rows)}, commit=True)
    return _csv("safetrail_tourists.csv", ["tourist_code", "name", "safety_status", "consent_given", "last_location_update", "sos_count"], rows)


@router.get("/api/v1/system/metrics")
def metrics(principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    from app.services.realtime import manager

    day = utc_now() - timedelta(hours=24)
    return {
        "uptime_seconds": int(time.time() - STARTED),
        **METRICS,
        "websocket": manager.stats(),
        "last_24h": {
            "sos": db.query(SOSAlert).filter(SOSAlert.created_at >= day).count(),
            "logins": db.query(AuditLog).filter(AuditLog.created_at >= day, AuditLog.action.in_(("STAFF_LOGIN", "TOURIST_LOGIN"))).count(),
            "failed_logins": db.query(AuditLog).filter(AuditLog.created_at >= day, AuditLog.action.like("%LOGIN_FAILED")).count(),
        },
    }
