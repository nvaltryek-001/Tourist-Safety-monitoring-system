"""Set (or reset) a staff password locally, e.g. after cloning or if demo
passwords were ever shared.  python -m app.scripts.set_password admin@demo.local
The new password is read from the terminal (not echoed, not logged)."""

from __future__ import annotations

import getpass
import sys

from app.core.security import hash_password, password_problems
from app.database import SessionLocal
from app.migrations import run_migrations
from app.database import engine
from app.models.models import StaffUser
from app.services.audit import audit


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.set_password <staff email>")
    email = sys.argv[1].strip().lower()
    run_migrations(engine)
    db = SessionLocal()
    try:
        user = db.query(StaffUser).filter_by(email=email).first()
        if user is None:
            raise SystemExit(f"No staff account {email}")
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Repeat: "):
            raise SystemExit("Passwords do not match")
        problems = password_problems(password)
        if problems:
            raise SystemExit("Password needs " + ", ".join(problems))
        user.password_hash = hash_password(password)
        user.failed_attempts, user.locked_until = 0, None
        audit(db, "STAFF_PASSWORD_RESET_CLI", "SYSTEM", None, f"staff:{user.id}")
        db.commit()
        print(f"Password updated for {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
