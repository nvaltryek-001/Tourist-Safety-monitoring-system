"""Authentication: passwordless tourist OTP and staff password login."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.core.security import (
    ROLE_TOURIST,
    as_utc,
    create_token,
    generate_otp,
    hash_otp,
    hash_password,
    normalize_email,
    otp_matches,
    password_problems,
    utc_now,
    verify_password,
)
from app.database import get_db
from app.deps import Principal, client_ip, get_principal, require_staff
from app.models.models import AuthSession, OTPCode, StaffUser, Tourist
from app.models.tourist_access import TouristAccess
from app.services.audit import audit
from app.services.notifications import send_otp_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class OTPRequest(BaseModel):
    email: str = Field(min_length=6, max_length=255)


class OTPVerify(BaseModel):
    email: str = Field(min_length=6, max_length=255)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    device_name: str | None = Field(default=None, max_length=120)


class StaffLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


def _rate_limit(key: str, limit: int, window: int) -> None:
    if not limiter.hit(key, limit, window):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait and try again.",
            headers={"Retry-After": str(limiter.retry_after(key, window))},
        )


def _issue(db: Session, subject: str, role: str, minutes: int, request: Request) -> dict:
    token, jti, expires = create_token(subject, role, minutes)
    db.add(AuthSession(
        jti=jti, subject=subject, role=role, expires_at=expires,
        user_agent=(request.headers.get("user-agent") or "")[:255], ip_address=client_ip(request),
    ))
    return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(), "role": role}


def find_access(db: Session, email: str) -> TouristAccess | None:
    wanted = normalize_email(email)
    for row in db.query(TouristAccess).filter_by(active=True).all():
        if normalize_email(row.email) == wanted:
            return row
    return None


# ------------------------------------------------------------------ tourist
@router.post("/tourist/request-otp")
def request_otp(data: OTPRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    email = data.email.strip().lower()
    domain = email.rpartition("@")[2]
    if "@" not in email or domain not in settings.tourist_email_domains:
        raise HTTPException(422, "Please use your Gmail address (…@gmail.com).")

    ip = client_ip(request)
    _rate_limit(f"otp-ip:{ip}", 10, settings.otp_window_seconds)
    _rate_limit(f"otp-email:{normalize_email(email)}", settings.otp_requests_per_window, settings.otp_window_seconds)

    access = find_access(db, email)
    if access is None or db.query(Tourist).filter_by(tourist_code=access.tourist_code).first() is None:
        audit(db, "TOURIST_OTP_REJECTED", "ANONYMOUS", None, None, {"reason": "not approved"}, ip, commit=True)
        raise HTTPException(403, "This Gmail address is not an approved tourist account. Contact the administrator.")

    # Invalidate earlier unused codes for this identity.
    for old in db.query(OTPCode).filter_by(email=normalize_email(email), used_at=None).all():
        old.used_at = utc_now()

    code = generate_otp()
    db.add(OTPCode(
        email=normalize_email(email),
        code_hash=hash_otp(normalize_email(email), code),
        expires_at=utc_now() + timedelta(seconds=settings.otp_ttl_seconds),
    ))
    delivery, error = send_otp_email(access.email, code)
    audit(db, "TOURIST_OTP_REQUESTED", "TOURIST", access.tourist_code, None, {"delivery": delivery}, ip)
    db.commit()

    response = {"expires_in_seconds": settings.otp_ttl_seconds, "delivery": delivery}
    if delivery == "ACCEPTED_BY_PROVIDER":
        response["message"] = "A login code was sent to your Gmail inbox."
    elif settings.otp_dev_echo:
        response["message"] = "Email is not configured. DEMO MODE: the code is shown here and was NOT emailed."
        response["dev_otp"] = code
    else:
        response["message"] = "The login code could not be emailed because email delivery is not configured. Contact the administrator."
        response["delivery_error"] = error
    return response


@router.post("/tourist/verify-otp")
def verify_otp(data: OTPVerify, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    email = normalize_email(data.email)
    ip = client_ip(request)
    _rate_limit(f"verify-ip:{ip}", 20, settings.otp_window_seconds)

    otp = (
        db.query(OTPCode).filter_by(email=email, used_at=None)
        .order_by(OTPCode.created_at.desc(), OTPCode.id.desc()).first()
    )
    invalid = HTTPException(401, "Invalid or expired code")
    if otp is None or as_utc(otp.expires_at) < utc_now():
        raise invalid
    if otp.attempts >= settings.otp_max_attempts:
        otp.used_at = utc_now()
        db.commit()
        raise HTTPException(429, "Too many wrong codes. Request a new code.")
    if not otp_matches(email, data.code, otp.code_hash):
        otp.attempts += 1
        audit(db, "TOURIST_LOGIN_FAILED", "ANONYMOUS", None, None, {"reason": "wrong code"}, ip)
        db.commit()
        raise invalid

    access = find_access(db, email)
    if access is None:
        raise invalid
    otp.used_at = utc_now()  # one-time use
    token = _issue(db, access.tourist_code, ROLE_TOURIST, settings.tourist_token_days * 24 * 60, request)
    audit(db, "TOURIST_LOGIN", "TOURIST", access.tourist_code, None, {"device": data.device_name}, ip)
    db.commit()
    tourist = db.query(Tourist).filter_by(tourist_code=access.tourist_code).first()
    return {**token, "tourist_code": access.tourist_code, "name": tourist.name if tourist else None}


# -------------------------------------------------------------------- staff
@router.post("/staff/login")
def staff_login(data: StaffLogin, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    ip = client_ip(request)
    _rate_limit(f"staff-login-ip:{ip}", 20, 300)
    email = data.email.strip().lower()
    user = db.query(StaffUser).filter_by(email=email).first()
    invalid = HTTPException(401, "Invalid email or password")

    if user is None or not user.active:
        verify_password(data.password, None)
        audit(db, "STAFF_LOGIN_FAILED", "ANONYMOUS", None, None, {"reason": "unknown or inactive"}, ip, commit=True)
        raise invalid
    if user.locked_until and as_utc(user.locked_until) > utc_now():
        raise HTTPException(423, "Account temporarily locked after failed logins. Try again later.")
    if not verify_password(data.password, user.password_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= settings.staff_max_failed_logins:
            user.locked_until = utc_now() + timedelta(minutes=settings.staff_lockout_minutes)
            user.failed_attempts = 0
        audit(db, "STAFF_LOGIN_FAILED", "STAFF", str(user.id), None, {"reason": "bad password"}, ip, commit=True)
        raise invalid

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = utc_now()
    token = _issue(db, str(user.id), user.role, settings.access_token_minutes, request)
    audit(db, "STAFF_LOGIN", "STAFF", str(user.id), None, None, ip)
    db.commit()
    return {**token, "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}


@router.post("/staff/change-password")
def change_password(
    data: PasswordChange,
    principal: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    user = principal.staff
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(401, "Current password is incorrect")
    problems = password_problems(data.new_password)
    if problems:
        raise HTTPException(422, "Password needs " + ", ".join(problems))
    user.password_hash = hash_password(data.new_password)
    # revoke every other session for this user
    for s in db.query(AuthSession).filter(AuthSession.subject == str(user.id), AuthSession.jti != principal.jti).all():
        s.revoked_at = s.revoked_at or utc_now()
    audit(db, "STAFF_PASSWORD_CHANGED", "STAFF", str(user.id), commit=False)
    db.commit()
    return {"message": "Password changed. Other sessions were signed out."}


# ------------------------------------------------------------------ shared
@router.get("/me")
def me(principal: Principal = Depends(get_principal)):
    data = {"role": principal.role, "subject": principal.subject, "name": principal.name}
    if principal.staff:
        s = principal.staff
        data.update({"id": s.id, "email": s.email, "badge_number": s.badge_number, "station": s.station})
    if principal.tourist:
        data["tourist_code"] = principal.tourist.tourist_code
    return data


@router.post("/logout")
def logout(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    session = db.query(AuthSession).filter_by(jti=principal.jti).first()
    if session:
        session.revoked_at = utc_now()
    audit(db, "LOGOUT", principal.actor_type, principal.subject)
    db.commit()
    return {"message": "Signed out"}


@router.get("/sessions")
def list_sessions(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    rows = (
        db.query(AuthSession)
        .filter(AuthSession.subject == principal.subject, AuthSession.role == principal.role,
                AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.desc()).limit(50).all()
    )
    now = utc_now()
    return [
        {"id": s.id, "created_at": s.created_at, "expires_at": s.expires_at, "user_agent": s.user_agent,
         "current": s.jti == principal.jti}
        for s in rows if as_utc(s.expires_at) > now
    ]


@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: int, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    s = db.get(AuthSession, session_id)
    if s is None or s.subject != principal.subject or s.role != principal.role:
        raise HTTPException(404, "Session not found")
    s.revoked_at = s.revoked_at or utc_now()
    audit(db, "SESSION_REVOKED", principal.actor_type, principal.subject, f"session:{s.id}")
    db.commit()
    return {"message": "Session revoked"}


@router.post("/sessions/revoke-others")
def revoke_other_sessions(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    count = 0
    for s in db.query(AuthSession).filter(
        AuthSession.subject == principal.subject, AuthSession.role == principal.role,
        AuthSession.jti != principal.jti, AuthSession.revoked_at.is_(None),
    ).all():
        s.revoked_at = utc_now()
        count += 1
    audit(db, "SESSIONS_REVOKED", principal.actor_type, principal.subject, None, {"count": count})
    db.commit()
    return {"revoked": count}
