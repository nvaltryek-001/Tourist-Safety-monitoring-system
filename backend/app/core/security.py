"""Password hashing, OTP generation and JWT helpers (stdlib + PyJWT only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

PBKDF2_ITERATIONS = 260_000
JWT_ALGORITHM = "HS256"

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_POLICE = "POLICE"
ROLE_TOURIST = "TOURIST"
STAFF_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_POLICE}
ADMIN_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ---------------------------------------------------------------- passwords
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, iterations, salt_b64, digest_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < 10:
        problems.append("at least 10 characters")
    if not any(c.isupper() for c in password):
        problems.append("an uppercase letter")
    if not any(c.islower() for c in password):
        problems.append("a lowercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("a digit")
    return problems


# ---------------------------------------------------------------------- OTP
def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, code: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{email.lower()}:{code}".encode(), hashlib.sha256).hexdigest()


def otp_matches(email: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(email, code), stored_hash)


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if domain in {"gmail.com", "googlemail.com"}:
        # Gmail ignores dots and +tags; normalise so one inbox = one identity.
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


# ---------------------------------------------------------------------- JWT
def create_token(subject: str, role: str, minutes: int, extra: dict | None = None) -> tuple[str, str, datetime]:
    settings = get_settings()
    jti = uuid.uuid4().hex
    expires = utc_now() + timedelta(minutes=minutes)
    payload = {
        "sub": subject,
        "role": role,
        "jti": jti,
        "iat": int(utc_now().timestamp()),
        "exp": int(expires.timestamp()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)
    return token, jti, expires


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().secret_key, algorithms=[JWT_ALGORITHM])
