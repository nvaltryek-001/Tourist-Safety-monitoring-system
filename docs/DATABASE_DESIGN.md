# Database design

## Original tables (preserved, never dropped)
| Table | Purpose | Added in v2 (nullable) |
|---|---|---|
| `tourists` | tourist profile + latest position | `location_accuracy`, `location_consent_at`, `expo_push_token`, `notify_push`, `notify_email` |
| `safety_zones` | circle zones (and optional polygon) | `risk_level`, `geometry_geojson`, `source`, `verification_status`, `created_at`, `updated_at` |
| `sos_alerts` | SOS incidents | `accuracy`, `alert_type`, `idempotency_key`, `assigned_officer_id`, `acknowledged_at`, `resolved_at`, `resolution_outcome`, `resolution_notes`, `updated_at` |
| `tourist_access` | Gmail allow-list for tourist login | — |

## New tables (schema v2)
`staff_users`, `otp_codes` (HMAC-hashed codes), `auth_sessions` (revocable JWT ids), `location_history`, `geofence_events`, `trips`, `incident_events` (SOS timeline), `notifications` (in-app + delivery log), `audit_logs`, `schema_version`.

## Indexes
`location_history(tourist_code, recorded_at)`, `geofence_events(tourist_code, created_at)`, `sos_alerts(status)`, `sos_alerts(idempotency_key)`, `safety_zones(active, zone_type)`, `notifications(dedupe_key)` unique, plus primary/unique keys.

## Migrations
`app/migrations.py` is additive only: creates missing tables, `ALTER TABLE … ADD COLUMN` for missing columns, creates indexes, records `schema_version`. Before the first change to a file-based SQLite DB it writes `backups/<name>_pre_migration_<UTC>.db` using SQLite's online backup API, and it aborts if any table has fewer rows afterwards.

```bash
python -m app.migrations --status                 # version + row counts
python -m app.migrations                          # upgrade (also runs on app start)
python -m app.migrations --restore backups/<file> # rollback (current DB is backed up first)
```
Why not Alembic: the existing DB has no Alembic history and could not be inspected from CI; stamping a guessed baseline risks a destructive autogenerate. The additive migrator is covered by `test_migration_upgrades_v1_database_without_losing_rows` (6 tourists / 209 zones / 5 SOS fixture → upgrade → counts preserved → idempotent re-run → restore).

## Backups
SQLite: automatic pre-migration copies + `sqlite3 tourist_safety.db ".backup backup.db"`. PostgreSQL: `pg_dump "$DATABASE_URL" > safetrail.sql` and `psql "$DATABASE_URL" < safetrail.sql` (see Deployment guide).
