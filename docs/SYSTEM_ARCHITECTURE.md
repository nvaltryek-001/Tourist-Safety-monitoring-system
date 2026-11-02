# System architecture

```
Tourist app (Expo) ──HTTPS──▶ FastAPI ──▶ PostgreSQL / SQLite
Dashboard (Next.js) ─HTTPS + WebSocket─▶ FastAPI ──▶ Email (Brevo/Resend/SMTP), Expo push
```

## Backend layout (`backend/app`)
| Layer | Files |
|---|---|
| Configuration | `core/config.py` (env vars, production checks) |
| Security | `core/security.py` (PBKDF2, OTP HMAC, JWT), `core/ratelimit.py`, `deps.py` (principal + role guards) |
| Models | `models/models.py`, `models/tourist_access.py` |
| Migrations | `migrations.py` (additive, backup, integrity check, restore) |
| Routers | `routers/legacy.py` (original v1.0 paths), `auth.py`, `me.py` (tourist), `zones.py`, `incidents.py` (SOS), `admin.py`, `operations.py` (analytics, AI, notifications, WebSocket, system) |
| Services | `tracking.py` (location ingest + geofence transitions), `geofence.py`, `geodata.py` (GeoJSON/KML, audit), `sos.py` (lifecycle), `notifications.py`, `intelligence.py`, `realtime.py`, `audit.py` |
| Scripts | `scripts/audit_db.py`, `scripts/copy_sqlite_to_postgres.py` |

## Request flow: location update
1. App posts `/api/v1/me/location` (or a batch from the offline queue) with a bearer token.
2. `deps.get_principal` verifies the JWT **and** the server-side session row (revocable).
3. `tracking.ingest_location` stores a `location_history` row, evaluates active zones, derives ENTER/EXIT events against the event log, updates the tourist's latest position only if the fix is newer, sends restricted-zone notifications, commits, then publishes `location.updated` / `geofence.event` over WebSocket.

## Real-time
`/ws` (token sent as the first `{"type":"auth"}` message, never in the URL, so it cannot leak into proxy/access logs) — staff receive all operational events; a tourist connection receives only its own SOS events. Fan-out is in-process (one instance, fits Render free). Scaling out would require Redis pub/sub; the publish interface stays the same.

## Roles
`SUPER_ADMIN` ⊃ `ADMIN` (manage tourists, zones, officers, audit) · `POLICE` (incidents, masked tourist list, contact details only during an active unassigned/own SOS) · `TOURIST` (only `/api/v1/me/*`, public zone reads).
