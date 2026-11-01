"""Notification service: in-app records + optional email / Expo push.

Delivery status vocabulary (never overstated):
  DELIVERED_IN_APP      – stored and visible in the app/dashboard inbox
  ACCEPTED_BY_PROVIDER  – the external provider accepted the request
                          (this is *not* proof the person received it)
  FAILED                – every attempt failed; see last_error
  NOT_CONFIGURED        – provider credentials missing; nothing was sent
  SKIPPED_PREFERENCE    – the recipient opted out of this channel
  DUPLICATE             – an identical notification already exists
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Notification, StaffUser, Tourist

log = logging.getLogger("app.notifications")

MAX_ATTEMPTS = 3
EMERGENCY_CATEGORIES = {"SOS_ALERT", "SOS_ACKNOWLEDGED", "EMERGENCY_RESPONSE"}

CATEGORIES = {
    "SOS_ALERT", "SOS_ACKNOWLEDGED", "EMERGENCY_RESPONSE", "RESTRICTED_ZONE_ENTRY",
    "HIGH_RISK_WARNING", "GEOFENCE_ENTRY", "GEOFENCE_EXIT", "SAFETY_ADVISORY",
    "ACCOUNT_VERIFICATION", "SYSTEM",
}


class ProviderError(Exception):
    pass


# --------------------------------------------------------------- providers
def send_email_resend(to: str, subject: str, text: str) -> None:
    import httpx

    settings = get_settings()
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.email_api_key}"},
        json={"from": settings.email_from, "to": [to], "subject": subject, "text": text},
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise ProviderError(f"email provider HTTP {response.status_code}")


def send_email_brevo(to: str, subject: str, text: str) -> None:
    """Brevo transactional email over HTTPS (free tier; works on hosts that block SMTP)."""
    import httpx

    settings = get_settings()
    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": settings.email_api_key, "accept": "application/json"},
        json={
            "sender": {"email": settings.email_from, "name": "SafeTrail Safety"},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": text,
        },
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise ProviderError(f"email provider HTTP {response.status_code}")


def send_email_smtp(to: str, subject: str, text: str) -> None:
    """Plain SMTP (e.g. Gmail app password). Many free hosts block SMTP ports."""
    import smtplib
    from email.message import EmailMessage

    settings = get_settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.email_from, to, subject
    msg.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        server.login(settings.smtp_username or settings.email_from, settings.email_api_key)
        server.send_message(msg)


EMAIL_SENDERS = {"resend": send_email_resend, "brevo": send_email_brevo, "smtp": send_email_smtp}


def send_email(to: str, subject: str, text: str) -> None:
    sender = EMAIL_SENDERS.get(get_settings().email_provider)
    if sender is None:
        raise ProviderError("unknown EMAIL_PROVIDER")
    sender(to, subject, text)


def send_expo_push(token: str, title: str, body: str, data: dict | None = None) -> None:
    import httpx

    settings = get_settings()
    headers = {"Content-Type": "application/json"}
    if settings.expo_access_token:
        headers["Authorization"] = f"Bearer {settings.expo_access_token}"
    response = httpx.post(
        "https://exp.host/--/api/v2/push/send",
        headers=headers,
        json={"to": token, "title": title, "body": body, "data": data or {}, "priority": "high", "sound": "default"},
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise ProviderError(f"push provider HTTP {response.status_code}")
    ticket = (response.json() or {}).get("data") or {}
    if isinstance(ticket, dict) and ticket.get("status") == "error":
        raise ProviderError(f"push ticket error: {ticket.get('message', '')[:120]}")


# Indirection so tests can swap providers without network access.
PROVIDERS: dict[str, Callable] = {"email": send_email, "push": send_expo_push}


def email_configured() -> bool:
    s = get_settings()
    return s.email_provider in EMAIL_SENDERS and bool(s.email_api_key and s.email_from)


def push_configured() -> bool:
    return get_settings().expo_push_enabled


def _with_retry(func: Callable, *args, attempts: int = MAX_ATTEMPTS) -> tuple[bool, int, str | None]:
    error = None
    for attempt in range(1, attempts + 1):
        try:
            func(*args)
            return True, attempt, None
        except Exception as exc:  # provider failures must never break the SOS flow
            error = str(exc)[:250] or exc.__class__.__name__
            log.warning("notification attempt %s failed: %s", attempt, error)
            if attempt < attempts:
                time.sleep(0.2 * attempt)
    return False, attempts, error


def _store(db: Session, **fields) -> Notification | None:
    note = Notification(**fields)
    if fields.get("dedupe_key"):
        existing = db.query(Notification).filter_by(dedupe_key=fields["dedupe_key"]).first()
        if existing:
            return None
    # The pre-check above prevents duplicates; the DB unique constraint is a
    # backstop. Also check objects added in this unit of work but not flushed.
    if fields.get("dedupe_key") and any(
        isinstance(obj, Notification) and obj.dedupe_key == fields["dedupe_key"] for obj in db.new
    ):
        return None
    db.add(note)
    return note


# --------------------------------------------------------------- public API
def notify_tourist(
    db: Session,
    tourist: Tourist,
    category: str,
    title: str,
    body: str,
    dedupe_key: str | None = None,
    related_sos_id: int | None = None,
) -> list[dict]:
    results = []
    note = _store(
        db, recipient_type="TOURIST", recipient_id=tourist.tourist_code, channel="IN_APP",
        category=category, title=title, body=body, status="DELIVERED_IN_APP", attempts=1,
        dedupe_key=f"{dedupe_key}:inapp" if dedupe_key else None, related_sos_id=related_sos_id,
    )
    if note is None:
        return [{"channel": "in_app", "status": "DUPLICATE"}]
    results.append({"channel": "in_app", "status": "DELIVERED_IN_APP"})

    push = Notification(
        recipient_type="TOURIST", recipient_id=tourist.tourist_code, channel="PUSH",
        category=category, title=title, body=body, related_sos_id=related_sos_id,
    )
    if tourist.notify_push is False and category not in EMERGENCY_CATEGORIES:
        push.status = "SKIPPED_PREFERENCE"
    elif not tourist.expo_push_token:
        push.status = "NOT_CONFIGURED"
        push.last_error = "tourist has no registered push token"
    elif not push_configured():
        push.status = "NOT_CONFIGURED"
        push.last_error = "EXPO_PUSH_ENABLED is false"
    else:
        ok, attempts, error = _with_retry(
            PROVIDERS["push"], tourist.expo_push_token, title, body, {"category": category, "sos_id": related_sos_id}
        )
        push.status, push.attempts, push.last_error = ("ACCEPTED_BY_PROVIDER" if ok else "FAILED"), attempts, error
    db.add(push)
    results.append({"channel": "push", "status": push.status})
    return results


def notify_staff(
    db: Session,
    category: str,
    title: str,
    body: str,
    roles: set[str] | None = None,
    dedupe_key: str | None = None,
    related_sos_id: int | None = None,
    email_admin: bool = False,
) -> list[dict]:
    roles = roles or {"SUPER_ADMIN", "ADMIN", "POLICE"}
    results = []
    staff = db.query(StaffUser).filter(StaffUser.active.is_(True), StaffUser.role.in_(roles)).all()
    stored = 0
    for user in staff:
        note = _store(
            db, recipient_type="STAFF", recipient_id=str(user.id), channel="IN_APP", category=category,
            title=title, body=body, status="DELIVERED_IN_APP", attempts=1,
            dedupe_key=f"{dedupe_key}:staff:{user.id}" if dedupe_key else None, related_sos_id=related_sos_id,
        )
        stored += 1 if note else 0
    results.append({"channel": "in_app", "recipients": stored, "status": "DELIVERED_IN_APP" if stored else "NONE"})

    settings = get_settings()
    if email_admin and settings.admin_alert_email:
        record = Notification(
            recipient_type="STAFF", recipient_id="admin-alert-email", channel="EMAIL",
            category=category, title=title, body=body, related_sos_id=related_sos_id,
        )
        if not email_configured():
            record.status, record.last_error = "NOT_CONFIGURED", "EMAIL_PROVIDER/EMAIL_API_KEY/EMAIL_FROM not set"
        else:
            ok, attempts, error = _with_retry(PROVIDERS["email"], settings.admin_alert_email, title, body)
            record.status, record.attempts, record.last_error = ("ACCEPTED_BY_PROVIDER" if ok else "FAILED"), attempts, error
        db.add(record)
        results.append({"channel": "email", "recipient_type": "admin", "status": record.status})
    return results


def notify_contact_email(db: Session, tourist: Tourist, title: str, body: str, related_sos_id: int | None) -> dict:
    if not tourist.emergency_contact_email:
        return {"channel": "email", "recipient_type": "emergency_contact", "status": "NO_CONTACT"}
    record = Notification(
        recipient_type="CONTACT", recipient_id=tourist.tourist_code, channel="EMAIL",
        category="SOS_ALERT", title=title, body=body, related_sos_id=related_sos_id,
    )
    if not email_configured():
        record.status, record.last_error = "NOT_CONFIGURED", "email provider not configured"
    else:
        ok, attempts, error = _with_retry(PROVIDERS["email"], tourist.emergency_contact_email, title, body)
        record.status, record.attempts, record.last_error = ("ACCEPTED_BY_PROVIDER" if ok else "FAILED"), attempts, error
    db.add(record)
    return {"channel": "email", "recipient_type": "emergency_contact", "status": record.status}


def send_otp_email(email: str, code: str) -> tuple[str, str | None]:
    """Returns (status, error). Never claims delivery without provider acceptance."""
    if not email_configured():
        return "NOT_CONFIGURED", "email provider not configured"
    minutes = max(1, get_settings().otp_ttl_seconds // 60)
    ok, _, error = _with_retry(
        PROVIDERS["email"], email, "Your Tourist Safety login code",
        f"Your one-time login code is {code}. It expires in {minutes} minutes. "
        "If you did not request it, ignore this email.",
    )
    return ("ACCEPTED_BY_PROVIDER" if ok else "FAILED"), error
