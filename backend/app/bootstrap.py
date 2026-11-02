"""Create the first staff accounts.

* BOOTSTRAP_ADMIN_EMAIL + BOOTSTRAP_ADMIN_PASSWORD -> a SUPER_ADMIN, created
  only if no account with that email exists (an existing password is never
  overwritten).
* SEED_DEMO_STAFF=true -> local demo accounts (superadmin@ / admin@ / police@demo.local).
  Passwords are NOT published: they come from DEMO_SUPERADMIN_PASSWORD /
  DEMO_ADMIN_PASSWORD / DEMO_POLICE_PASSWORD if set, otherwise a random strong
  password is generated and written once to backend/demo_credentials.txt
  (git-ignored). Ignored when ENVIRONMENT=production.
"""

from __future__ import annotations

import logging
import os
import secrets
import string
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, password_problems
from app.models.models import StaffUser
from app.services.audit import audit

log = logging.getLogger("app.bootstrap")

DEMO_STAFF = (
    ("superadmin@demo.local", "Demo Super Admin", "SUPER_ADMIN", "DEMO_SUPERADMIN_PASSWORD", None),
    ("admin@demo.local", "Demo Admin", "ADMIN", "DEMO_ADMIN_PASSWORD", None),
    ("police@demo.local", "Demo Officer", "POLICE", "DEMO_POLICE_PASSWORD", "KA-DEMO-001"),
)
CREDENTIALS_FILE = Path(__file__).resolve().parents[1] / "demo_credentials.txt"


def generate_password(length: int = 14) -> str:
    """Random password that satisfies the staff policy (upper, lower, digit, 10+ chars)."""
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isupper() for c in pw) and any(c.islower() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def _ensure(db: Session, email: str, name: str, role: str, password: str, badge: str | None) -> bool:
    if db.query(StaffUser).filter_by(email=email).first():
        return False
    db.add(StaffUser(email=email, name=name, role=role, password_hash=hash_password(password), badge_number=badge))
    audit(db, "STAFF_BOOTSTRAPPED", "SYSTEM", None, email, {"role": role})
    return True


def bootstrap_staff(db: Session) -> list[str]:
    settings = get_settings()
    created = []
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        problems = password_problems(settings.bootstrap_admin_password)
        if problems:
            log.error("BOOTSTRAP_ADMIN_PASSWORD rejected: needs %s", ", ".join(problems))
        elif _ensure(db, settings.bootstrap_admin_email.strip().lower(), "Super Admin", "SUPER_ADMIN",
                     settings.bootstrap_admin_password, None):
            created.append(settings.bootstrap_admin_email)
    if settings.seed_demo_staff:
        if settings.is_production:
            log.warning("SEED_DEMO_STAFF ignored because ENVIRONMENT=production")
        else:
            written = []
            for email, name, role, env_name, badge in DEMO_STAFF:
                password = os.getenv(env_name) or generate_password()
                if _ensure(db, email, name, role, password, badge):
                    created.append(email)
                    if not os.getenv(env_name):
                        written.append(f"{role:12s} {email:24s} {password}")
            if written:
                try:
                    with CREDENTIALS_FILE.open("a", encoding="utf-8") as fh:
                        fh.write("# SafeTrail local demo accounts (generated; never commit this file)\n")
                        fh.write("\n".join(written) + "\n")
                    log.warning("Demo staff passwords written to %s", CREDENTIALS_FILE)
                except OSError:
                    log.error("Could not write %s; set DEMO_*_PASSWORD env vars instead", CREDENTIALS_FILE)
    db.commit()
    if created:
        log.info("Bootstrapped staff accounts: %s", ", ".join(created))
    return created
