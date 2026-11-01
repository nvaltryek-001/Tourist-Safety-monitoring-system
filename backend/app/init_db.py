"""Create or upgrade the database schema (additive, with SQLite backup)."""

import json

from app.database import engine
from app.migrations import run_migrations


def init_db():
    report = run_migrations(engine)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    init_db()
