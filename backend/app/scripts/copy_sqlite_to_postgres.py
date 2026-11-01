"""Copy every row from the local SQLite database into an empty PostgreSQL DB.

This is how the six existing tourists, their Gmail login list, the safety
zones and the SOS history reach a hosted database without being re-typed.

Usage (from backend/):
    python -m app.scripts.copy_sqlite_to_postgres \
        --source sqlite:///./tourist_safety.db \
        --target "postgresql://USER:PASS@HOST/DB"

Safety:
* the source SQLite file is opened read-only and never modified;
* the target schema is created/upgraded with the same additive migrator;
* the copy refuses to run if any target table already has rows (use
  --allow-non-empty only if you know what you are doing);
* primary keys are preserved so zone IDs (e.g. College Demo Zones) match;
* row counts are compared after the copy.
"""

from __future__ import annotations

import argparse

from sqlalchemy import MetaData, create_engine, func, select, text

import app.models  # noqa: F401
from app.database import Base, _normalise_url
from app.migrations import run_migrations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="sqlite:///./tourist_safety.db")
    parser.add_argument("--target", required=True)
    parser.add_argument("--allow-non-empty", action="store_true")
    args = parser.parse_args()

    src_url = args.source
    if src_url.startswith("sqlite:///") and "mode=ro" not in src_url:
        src_url = "sqlite:///file:" + src_url[len("sqlite:///"):] + "?mode=ro&uri=true"
    source = create_engine(src_url)
    target = create_engine(_normalise_url(args.target))

    run_migrations(target, backup=False)
    src_meta = MetaData()
    src_meta.reflect(bind=source)

    with target.begin() as tconn:
        for table in Base.metadata.sorted_tables:
            if table.name == "schema_version":
                continue
            existing = tconn.execute(select(func.count()).select_from(table)).scalar_one()
            if existing and not args.allow_non_empty:
                raise SystemExit(f"Target table {table.name} already has {existing} rows; aborting.")

    copied = {}
    with source.connect() as sconn, target.begin() as tconn:
        for table in Base.metadata.sorted_tables:
            if table.name == "schema_version" or table.name not in src_meta.tables:
                continue
            src_table = src_meta.tables[table.name]
            shared = [c.name for c in src_table.columns if c.name in table.columns]
            rows = [dict(r._mapping) for r in sconn.execute(select(*[src_table.c[n] for n in shared]))]
            for row in rows:
                for col in table.columns:
                    if col.name in row and row[col.name] is not None and str(col.type) == "BOOLEAN":
                        row[col.name] = bool(row[col.name])
            if rows:
                tconn.execute(table.insert(), rows)
            copied[table.name] = len(rows)
            if "id" in table.columns and rows and target.dialect.name == "postgresql":
                tconn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"(SELECT COALESCE(MAX(id), 1) FROM \"{table.name}\"))"
                ))

    with target.connect() as tconn:
        for name, count in copied.items():
            table = Base.metadata.tables[name]
            now = tconn.execute(select(func.count()).select_from(table)).scalar_one()
            status = "OK" if now >= count else "MISMATCH"
            print(f"{name:20s} source={count:6d} target={now:6d} {status}")


if __name__ == "__main__":
    main()
