import json
import logging

from sqlalchemy.orm import Session

from app.models.models import AuditLog

log = logging.getLogger("app.audit")


def audit(
    db: Session,
    action: str,
    actor_type: str = "SYSTEM",
    actor_id: str | None = None,
    target: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
    commit: bool = False,
) -> None:
    """Record an audit entry. Never put secrets, OTPs or raw locations in detail."""
    db.add(AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target=target,
        detail=json.dumps(detail, default=str) if detail else None,
        ip_address=ip,
    ))
    log.info("audit action=%s actor=%s:%s target=%s", action, actor_type, actor_id, target)
    if commit:
        db.commit()
