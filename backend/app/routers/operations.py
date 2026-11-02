"""Analytics, AI intelligence, staff notifications, WebSocket and system status."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import as_utc, utc_now
from app.database import SessionLocal, get_db
from app.deps import Principal, principal_from_token, require_admin, require_staff
from app.models.models import AuditLog, GeofenceEvent, LocationPoint, Notification, SafetyZone, SOSAlert, Tourist
from app.services import intelligence
from app.services.geodata import is_synthetic
from app.services.notifications import email_configured, push_configured
from app.services.realtime import Connection, manager
from app.services.tracking import ACTIVE_SOS_STATUSES

router = APIRouter(tags=["operations"])


# ---------------------------------------------------------------- helpers
def _assessments(db: Session, hours: int = 24) -> list[dict]:
    since = utc_now() - timedelta(hours=hours)
    points_by: dict[str, list] = {}
    for r in db.query(LocationPoint).filter(LocationPoint.recorded_at >= since).all():
        points_by.setdefault(r.tourist_code, []).append(
            intelligence.Point(r.latitude, r.longitude, as_utc(r.recorded_at), r.accuracy))
    events_by: dict[str, list] = {}
    for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since).all():
        events_by.setdefault(e.tourist_code, []).append(
            {"event_type": e.event_type, "zone_id": e.zone_id, "zone_name": e.zone_name,
             "zone_type": e.zone_type, "created_at": as_utc(e.created_at)})
    open_sos = Counter(a.tourist_code for a in db.query(SOSAlert).filter(SOSAlert.status.in_(ACTIVE_SOS_STATUSES)).all())
    out = []
    for t in db.query(Tourist).all():
        result = intelligence.assess_tourist(points_by.get(t.tourist_code, []), events_by.get(t.tourist_code, []),
                                             open_sos=open_sos.get(t.tourist_code, 0))
        out.append({"tourist_code": t.tourist_code, "name": t.name, "safety_status": t.safety_status,
                    "risk_score": result["risk_score"], "risk_level": result["risk_level"],
                    "advisories": result["advisories"], "kind": result["kind"]})
    return sorted(out, key=lambda r: r["risk_score"], reverse=True)


def _alert_dicts(db: Session) -> list[dict]:
    return [
        {"created_at": as_utc(a.created_at), "status": a.status, "alert_type": a.alert_type,
         "acknowledged_at": as_utc(a.acknowledged_at), "latitude": a.latitude, "longitude": a.longitude}
        for a in db.query(SOSAlert).all()
    ]


def _zone_rows(db: Session) -> list[dict]:
    since = utc_now() - timedelta(days=30)
    zones = [
        {"id": z.id, "name": z.name, "latitude": z.latitude, "longitude": z.longitude,
         "radius_meters": z.radius_meters, "zone_type": z.zone_type, "risk_level": z.risk_level}
        for z in db.query(SafetyZone).filter_by(active=True).all()
    ]
    events = [{"zone_id": e.zone_id, "event_type": e.event_type}
              for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since).all()]
    return intelligence.zone_risk(zones, events, _alert_dicts(db))


# -------------------------------------------------------------- analytics
@router.get("/api/v1/analytics/overview", tags=["analytics"])
def overview(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    settings = get_settings()
    now = utc_now()
    cutoff = now - timedelta(minutes=settings.stale_location_minutes)
    tourists = db.query(Tourist).all()
    alerts = db.query(SOSAlert).all()
    zones = db.query(SafetyZone).all()
    status_counts = Counter(t.safety_status for t in tourists)
    active = [t for t in tourists if t.last_location_update and as_utc(t.last_location_update) >= cutoff]
    attention = [t for t in tourists if t.safety_status in {"DANGER", "SOS", "CAUTION"}]
    recent = sorted(alerts, key=lambda a: a.id, reverse=True)[:8]
    zone_types = Counter(z.zone_type for z in zones if z.active)
    risk_levels = Counter((z.risk_level or "UNSET") for z in zones if z.active)
    events = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(12).all() if principal.is_admin else []
    return {
        "generated_at": now,
        "kpis": {
            "registered_tourists": len(tourists),
            "active_tourists": len(active),
            "tourists_requiring_attention": len(attention),
            "active_sos": sum(1 for a in alerts if a.status == "OPEN"),
            "open_incidents": sum(1 for a in alerts if a.status in ACTIVE_SOS_STATUSES),
            "resolved_incidents": sum(1 for a in alerts if a.status == "RESOLVED"),
            "safety_zones": len(zones),
            "active_zones": sum(1 for z in zones if z.active),
            "synthetic_zones": sum(1 for z in zones if is_synthetic(z.name, z.description)),
        },
        "tourist_status_distribution": dict(status_counts),
        "zone_type_distribution": dict(zone_types),
        "zone_risk_distribution": dict(risk_levels),
        "recent_sos": [
            {"id": a.id, "tourist_code": a.tourist_code, "status": a.status, "alert_type": a.alert_type or "GENERAL",
             "created_at": a.created_at} for a in recent
        ],
        "recent_events": [
            {"id": e.id, "action": e.action, "actor_type": e.actor_type, "target": e.target, "created_at": e.created_at}
            for e in events
        ],
        "stale_after_minutes": settings.stale_location_minutes,
    }


@router.get("/api/v1/analytics/trends", tags=["analytics"])
def trends(days: int = Query(default=30, ge=7, le=180), principal: Principal = Depends(require_staff),
           db: Session = Depends(get_db)):
    data = intelligence.incident_trends(_alert_dicts(db), days=days)
    since = utc_now() - timedelta(days=days)
    geo = Counter()
    for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since, GeofenceEvent.event_type == "ENTER").all():
        geo[as_utc(e.created_at).date().isoformat()] += 1
    data["restricted_entries_daily"] = [{"date": d["date"], "count": geo.get(d["date"], 0)} for d in data["daily"]]
    return data


@router.get("/api/v1/analytics/hotspots", tags=["analytics"])
def hotspots(
    days: int = Query(default=90, ge=1, le=730),
    cell_m: int = Query(default=500, ge=100, le=5000),
    min_count: int = Query(default=2, ge=1, le=50),
    include_zone_entries: bool = True,
    principal: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    since = utc_now() - timedelta(days=days)
    pts = [{"latitude": a.latitude, "longitude": a.longitude, "kind": f"SOS_{a.alert_type or 'GENERAL'}", "created_at": as_utc(a.created_at)}
           for a in db.query(SOSAlert).filter(SOSAlert.created_at >= since).all()]
    if include_zone_entries:
        pts += [{"latitude": e.latitude, "longitude": e.longitude, "kind": "RESTRICTED_ENTRY", "created_at": as_utc(e.created_at)}
                for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since, GeofenceEvent.event_type == "ENTER",
                                                       GeofenceEvent.zone_type.in_(("RESTRICTED", "HIGH_RISK"))).all()]
    return {"window_days": days, **intelligence.grid_hotspots(pts, cell_m, min_count)}


@router.get("/api/v1/analytics/response-times", tags=["analytics"])
def response_time_stats(days: int = Query(default=90, ge=1, le=730), principal: Principal = Depends(require_staff),
                        db: Session = Depends(get_db)):
    from app.models.models import StaffUser

    since = utc_now() - timedelta(days=days)
    officers = {u.id: u.name for u in db.query(StaffUser).all()}
    alerts = [{"created_at": as_utc(a.created_at), "acknowledged_at": as_utc(a.acknowledged_at), "resolved_at": as_utc(a.resolved_at),
               "status": a.status, "alert_type": a.alert_type, "resolution_outcome": a.resolution_outcome,
               "officer": officers.get(a.assigned_officer_id)}
              for a in db.query(SOSAlert).filter(SOSAlert.created_at >= since).all()]
    return {"window_days": days, **intelligence.response_times(alerts)}


@router.get("/api/v1/analytics/zone-activity", tags=["analytics"])
def zone_activity(days: int = Query(default=30, ge=1, le=365), principal: Principal = Depends(require_staff),
                  db: Session = Depends(get_db)):
    since = utc_now() - timedelta(days=days)
    events = [{"tourist_code": e.tourist_code, "zone_id": e.zone_id, "zone_name": e.zone_name, "zone_type": e.zone_type,
               "event_type": e.event_type, "created_at": as_utc(e.created_at)}
              for e in db.query(GeofenceEvent).filter(GeofenceEvent.created_at >= since).all()]
    return {"window_days": days, "events": len(events), "zones": intelligence.zone_activity(events)}


@router.get("/api/v1/analytics/movement", tags=["analytics"])
def movement(hours: int = Query(default=24, ge=1, le=24 * 30), principal: Principal = Depends(require_admin),
             db: Session = Depends(get_db)):
    since = utc_now() - timedelta(hours=hours)
    by: dict[str, list] = {}
    for r in db.query(LocationPoint).filter(LocationPoint.recorded_at >= since).all():
        by.setdefault(r.tourist_code, []).append(intelligence.Point(r.latitude, r.longitude, as_utc(r.recorded_at), r.accuracy))
    return {"window_hours": hours, "tourists": intelligence.movement_summary(by)}


# ---------------------------------------------------------- intelligence
@router.get("/api/v1/intelligence/tourists", tags=["ai intelligence"])
def ai_tourists(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    return _assessments(db)


@router.get("/api/v1/intelligence/zones", tags=["ai intelligence"])
def ai_zones(limit: int = Query(default=25, ge=1, le=500), principal: Principal = Depends(require_staff),
             db: Session = Depends(get_db)):
    return _zone_rows(db)[:limit]


@router.get("/api/v1/intelligence/report", tags=["ai intelligence"])
def ai_report(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    return intelligence.hazard_report(_zone_rows(db), intelligence.incident_trends(_alert_dicts(db)), _assessments(db))


# --------------------------------------------------------- notifications
@router.get("/api/v1/notifications", tags=["notifications"])
def staff_notifications(unread_only: bool = False, principal: Principal = Depends(require_staff),
                        db: Session = Depends(get_db)):
    q = db.query(Notification).filter_by(recipient_type="STAFF", recipient_id=principal.subject, channel="IN_APP")
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.id.desc()).limit(100).all()
    return [
        {"id": n.id, "category": n.category, "title": n.title, "body": n.body, "created_at": n.created_at,
         "read_at": n.read_at, "related_sos_id": n.related_sos_id}
        for n in rows
    ]


@router.post("/api/v1/notifications/{note_id}/read", tags=["notifications"])
def staff_read(note_id: int, principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    n = db.get(Notification, note_id)
    if n is None or n.recipient_type != "STAFF" or n.recipient_id != principal.subject:
        raise HTTPException(404, "Notification not found")
    n.read_at = n.read_at or utc_now()
    db.commit()
    return {"id": n.id, "read_at": n.read_at}


@router.post("/api/v1/notifications/read-all", tags=["notifications"])
def staff_read_all(principal: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    count = 0
    for n in db.query(Notification).filter_by(recipient_type="STAFF", recipient_id=principal.subject,
                                              channel="IN_APP", read_at=None).all():
        n.read_at = utc_now()
        count += 1
    db.commit()
    return {"marked": count}


@router.get("/api/v1/notifications/delivery-log", tags=["notifications"])
def delivery_log(channel: str | None = None, status: str | None = None,
                 principal: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(Notification)
    if channel:
        q = q.filter(Notification.channel == channel.upper())
    if status:
        q = q.filter(Notification.status == status.upper())
    rows = q.order_by(Notification.id.desc()).limit(200).all()
    return {
        "providers": {"email": "configured" if email_configured() else "not configured",
                      "push": "enabled" if push_configured() else "disabled", "sms": "not configured"},
        "items": [
            {"id": n.id, "recipient_type": n.recipient_type, "recipient_id": n.recipient_id, "channel": n.channel,
             "category": n.category, "title": n.title, "status": n.status, "attempts": n.attempts,
             "last_error": n.last_error, "created_at": n.created_at, "related_sos_id": n.related_sos_id}
            for n in rows
        ],
    }


# ------------------------------------------------------------- websocket
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    db = SessionLocal()
    try:
        principal = principal_from_token(token, db)
    except HTTPException:
        await websocket.close(code=4401)
        return
    finally:
        db.close()
    await websocket.accept()
    conn = Connection(websocket=websocket, role=principal.role, subject=principal.subject)
    manager.register(conn)
    await websocket.send_json({"type": "hello", "data": {"role": principal.role}})

    async def sender():
        while True:
            message = await conn.queue.get()
            await websocket.send_text(message)

    send_task = asyncio.create_task(sender())
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        manager.unregister(conn)


# ---------------------------------------------------------------- system
@router.get("/api/v1/system/health", tags=["system"])
def system_health():
    return {"status": "healthy", "time": utc_now()}


@router.get("/ready", tags=["system"])
@router.get("/api/v1/system/ready", tags=["system"])
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable")
    return {"status": "ready", "database": "ok"}


@router.get("/api/v1/system/info", tags=["system"])
def system_info(principal: Principal = Depends(require_admin)):
    from app.database import engine
    from app.migrations import current_version

    s = get_settings()
    return {
        "environment": s.environment,
        "database_dialect": engine.dialect.name,
        "schema_version": current_version(engine),
        "email_provider": s.email_provider if email_configured() else "not configured",
        "push_notifications": "enabled" if push_configured() else "disabled",
        "otp_dev_echo": s.otp_dev_echo,
        "location_retention_days": s.location_retention_days,
        "websocket": manager.stats(),
        "allowed_origins": s.allowed_origins,
    }
