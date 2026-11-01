"""Create the first staff accounts.

* BOOTSTRAP_ADMIN_EMAIL + BOOTSTRAP_ADMIN_PASSWORD -> a SUPER_ADMIN, created
  only if no account with that email exists (an existing password is never
  overwritten).
* SEED_DEMO_STAFF=true -> local demo accounts with documented passwords.
  Never enable this on a public deployment.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, password_problems
from app.models.models import StaffUser
from app.services.audit import audit

log = logging.getLogger("app.bootstrap")

DEMO_STAFF = (
    ("superadmin@demo.local", "Demo Super Admin", "SUPER_ADMIN", "SuperAdmin@123", None),
    ("admin@demo.local", "Demo Admin", "ADMIN", "Admin@12345", None),
    ("police@demo.local", "Demo Officer", "POLICE", "Police@12345", "KA-DEMO-001"),
)


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
            for row in DEMO_STAFF:
                if _ensure(db, *row):
                    created.append(row[0])
    db.commit()
    if created:
        log.info("Bootstrapped staff accounts: %s", ", ".join(created))
    return created
