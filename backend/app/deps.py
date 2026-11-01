"""FastAPI dependencies: database session, current principal, role checks."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import ADMIN_ROLES, ROLE_TOURIST, STAFF_ROLES, as_utc, decode_token, utc_now
from app.database import get_db
from app.models.models import AuthSession, StaffUser, Tourist

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    role: str
    subject: str  # tourist_code for tourists, staff id for staff
    jti: str
    name: str
    staff: StaffUser | None = None
    tourist: Tourist | None = None

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES

    @property
    def actor_type(self) -> str:
        return "STAFF" if self.is_staff else "TOURIST"


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


def principal_from_token(token: str, db: Session) -> Principal:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise unauthorized
    session = db.query(AuthSession).filter_by(jti=payload.get("jti")).first()
    if session is None or session.revoked_at is not None or as_utc(session.expires_at) < utc_now():
        raise unauthorized
    role = payload.get("role")
    subject = str(payload.get("sub"))
    if role == ROLE_TOURIST:
        tourist = db.query(Tourist).filter_by(tourist_code=subject).first()
        if tourist is None:
            raise unauthorized
        return Principal(role=role, subject=subject, jti=session.jti, name=tourist.name, tourist=tourist)
    if role in STAFF_ROLES:
        staff = db.get(StaffUser, int(subject)) if subject.isdigit() else None
        if staff is None or not staff.active or staff.role != role:
            raise unauthorized
        return Principal(role=role, subject=subject, jti=session.jti, name=staff.name, staff=staff)
    raise unauthorized


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal_from_token(credentials.credentials, db)


def require_roles(*roles: str):
    allowed = set(roles)

    def checker(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return principal

    return checker


require_staff = require_roles(*STAFF_ROLES)
require_admin = require_roles(*ADMIN_ROLES)
require_super_admin = require_roles("SUPER_ADMIN")
require_tourist = require_roles(ROLE_TOURIST)


def require_tourist_or_staff_for(tourist_code: str, principal: Principal) -> None:
    """Tourists may act only on themselves; staff may act on anyone."""
    if principal.is_staff:
        return
    if principal.role == ROLE_TOURIST and principal.subject == tourist_code:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only access your own data")
