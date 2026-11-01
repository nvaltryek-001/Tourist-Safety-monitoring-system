"""Read-only database audit. Prints counts and zone reconciliation, no PII.

Usage (from backend/):  python -m app.scripts.audit_db [--json report.json]
It never writes to the database.
"""

from __future__ import annotations

import argparse
import json

from sqlalchemy import inspect

from app.database import SessionLocal, engine
from app.migrations import current_version, table_counts
from app.services.geodata import audit_zones


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="also write the report to this file")
    args = parser.parse_args()

    tables = set(inspect(engine).get_table_names())
    report: dict = {"database": engine.url.render_as_string(hide_password=True),
                    "schema_version": current_version(engine), "table_counts": table_counts(engine)}
    db = SessionLocal()
    try:
        if "safety_zones" in tables:
            # Query with only the original columns so this works on a v1 database.
            from collections import namedtuple

            Row = namedtuple("Row", "id name latitude longitude radius_meters zone_type description active")
            rows = [Row(*r) for r in db.execute(
                __import__("sqlalchemy").text(
                    "SELECT id, name, latitude, longitude, radius_meters, zone_type, description, active FROM safety_zones"
                )
            ).all()]
            zone_report = audit_zones(rows)
            zone_report.pop("overlap_pairs_sample", None)
            report["zones"] = zone_report
            synthetic = zone_report["synthetic_zones"]
            college = zone_report["college_demo_zones"]
            report["zone_reconciliation"] = {
                "total": zone_report["total_zones"],
                "synthetic_DEMO_KA": synthetic,
                "college_demo": college,
                "other": zone_report["total_zones"] - synthetic - college,
                "college_included_in_total": True,
            }
        if "tourist_access" in tables:
            from sqlalchemy import text

            emails = [r[0] for r in db.execute(text("SELECT email FROM tourist_access WHERE active = 1 OR active = true")).all()]
            report["tourist_access"] = {
                "active_rows": len(emails),
                "gmail_rows": sum(1 for e in emails if e.lower().endswith(("@gmail.com", "@googlemail.com"))),
            }
    finally:
        db.close()

    text_out = json.dumps(report, indent=2, default=str)
    print(text_out)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text_out)


if __name__ == "__main__":
    main()
