"""Additive, idempotent schema migrations with automatic SQLite backup.

Why not Alembic? The project's existing SQLite database was created with
``Base.metadata.create_all`` and has no Alembic history. Every change in
schema v2 is *additive* (new tables, new nullable columns, new indexes), so a
small, auditable migrator is safer than stamping a guessed Alembic baseline
onto a database we cannot inspect from CI. Rules enforced here:

* never drop or rename a table or column;
* back up a file-based SQLite database before the first change;
* verify that no table lost rows during the upgrade, otherwise raise;
* record each applied version in ``schema_version``.

Rollback: ``python -m app.migrations --restore <backup-file>`` copies a backup
back over the SQLite database (the current file is itself backed up first).
For PostgreSQL use ``pg_dump``/``pg_restore`` (see docs/DEPLOYMENT_GUIDE.md).
"""

from __future__ import annotations

import argparse
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import app.models  # noqa: F401 - registers all tables on Base.metadata
from app.database import Base

log = logging.getLogger("app.migrations")

CURRENT_SCHEMA_VERSION = 2
PROTECTED_TABLES = ("tourists", "safety_zones", "sos_alerts", "tourist_access")
EXTRA_INDEXES = {
    "ix_sos_alerts_idempotency_key": ("sos_alerts", "idempotency_key"),
    "ix_sos_alerts_status": ("sos_alerts", "status"),
    "ix_safety_zones_active_type": ("safety_zones", "active, zone_type"),
}


def sqlite_path(engine: Engine) -> Path | None:
    if engine.dialect.name != "sqlite":
        return None
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    return Path(database).resolve()


def backup_sqlite(engine: Engine, label: str = "pre_migration") -> Path | None:
    path = sqlite_path(engine)
    if path is None or not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{path.stem}_{label}_{stamp}{path.suffix}"
    # Use SQLite's online backup API so a live database is copied consistently.
    import sqlite3

    with sqlite3.connect(path) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    log.info("SQLite backup written to %s", target)
    return target


def table_counts(engine: Engine) -> dict[str, int]:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    counts = {}
    with engine.connect() as conn:
        for table in sorted(existing):
            counts[table] = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
    return counts


def current_version(engine: Engine) -> int:
    inspector = inspect(engine)
    if "schema_version" not in inspector.get_table_names():
        return 1 if "tourists" in inspector.get_table_names() else 0
    with engine.connect() as conn:
        value = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
    return int(value or 1)


def _missing_columns(engine: Engine) -> list[tuple[str, str, str]]:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            col_type = column.type.compile(dialect=engine.dialect)
            missing.append((table.name, column.name, col_type))
    return missing


def run_migrations(engine: Engine, backup: bool = True) -> dict:
    """Upgrade the database in place. Returns a report dictionary."""
    before_version = current_version(engine)
    before_counts = table_counts(engine)
    missing = _missing_columns(engine)
    existing_tables = set(inspect(engine).get_table_names())
    new_tables = [t.name for t in Base.metadata.sorted_tables if t.name not in existing_tables]

    needs_change = bool(missing or new_tables or before_version < CURRENT_SCHEMA_VERSION)
    backup_file = None
    if needs_change and backup and before_counts:
        backup_file = backup_sqlite(engine)

    Base.metadata.create_all(bind=engine)  # creates only missing tables

    with engine.begin() as conn:
        for table, column, col_type in missing:
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}'))
            log.info("Added column %s.%s", table, column)

    inspector = inspect(engine)
    with engine.begin() as conn:
        for name, (table, columns) in EXTRA_INDEXES.items():
            existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
            if name not in existing_indexes:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" ({columns})'))

    after_counts = table_counts(engine)
    for table, count in before_counts.items():
        if after_counts.get(table, 0) < count:
            raise RuntimeError(
                f"Migration integrity check failed: {table} had {count} rows, now {after_counts.get(table)}"
            )

    if before_version < CURRENT_SCHEMA_VERSION:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO schema_version (version, applied_at, note) VALUES (:v, :t, :n)"),
                {"v": CURRENT_SCHEMA_VERSION, "t": datetime.now(timezone.utc), "n": "additive v2 upgrade"},
            )

    return {
        "from_version": before_version,
        "to_version": CURRENT_SCHEMA_VERSION,
        "new_tables": new_tables,
        "added_columns": [f"{t}.{c}" for t, c, _ in missing],
        "backup_file": str(backup_file) if backup_file else None,
        "protected_counts_before": {t: before_counts.get(t) for t in PROTECTED_TABLES if t in before_counts},
        "protected_counts_after": {t: after_counts.get(t) for t in PROTECTED_TABLES if t in after_counts},
    }


def restore_sqlite(engine: Engine, backup_file: Path) -> Path | None:
    path = sqlite_path(engine)
    if path is None:
        raise RuntimeError("Restore is only supported for file-based SQLite databases")
    if not backup_file.exists():
        raise FileNotFoundError(backup_file)
    engine.dispose()
    safety_copy = backup_sqlite(engine, label="before_restore")
    shutil.copy2(backup_file, path)
    return safety_copy


def main() -> None:  # pragma: no cover - CLI wrapper
    import json

    from app.database import engine

    parser = argparse.ArgumentParser(description="Database migration utility")
    parser.add_argument("--restore", type=Path, help="restore this SQLite backup file")
    parser.add_argument("--status", action="store_true", help="print schema version and counts only")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.status:
        print(json.dumps({"version": current_version(engine), "counts": table_counts(engine)}, indent=2))
    elif args.restore:
        safety = restore_sqlite(engine, args.restore)
        print(f"Restored {args.restore}. Previous database saved to {safety}")
    else:
        print(json.dumps(run_migrations(engine), indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    main()
