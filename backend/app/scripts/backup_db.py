"""Back up the database.  python -m app.scripts.backup_db [--out backups/]

* SQLite: consistent online copy via the sqlite3 backup API.
* PostgreSQL: runs pg_dump (custom format) if it is installed.
Restore: SQLite -> python -m app.migrations --restore <file>;
PostgreSQL -> pg_restore --clean -d "$DATABASE_URL" <file>.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.database import DATABASE_URL, engine
from app.migrations import backup_sqlite


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="backups")
    args = parser.parse_args()
    if engine.dialect.name == "sqlite":
        path = backup_sqlite(engine, label="manual")
        print(f"SQLite backup: {path}" if path else "Nothing to back up (in-memory or missing database)")
        return
    if not shutil.which("pg_dump"):
        raise SystemExit("pg_dump not found. Install PostgreSQL client tools, or use the Render dashboard backups.")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"safetrail_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.dump"
    url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    subprocess.run(["pg_dump", "--format=custom", "--no-owner", f"--file={target}", url], check=True)
    print(f"PostgreSQL backup: {target}")


if __name__ == "__main__":
    main()
