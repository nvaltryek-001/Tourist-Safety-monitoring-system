# SOS workflow

```
Tourist holds SOS 1.5 s ─▶ app gets fresh GPS fix ─▶ confirmation screen ─▶ POST /api/v1/me/sos (idempotency_key)
      ─▶ server creates alert #id (OPEN) + timeline "CREATED" + audit ─▶ response server_confirmed=true
      ─▶ staff in-app notifications, admin email, emergency-contact email (if configured), tourist "SOS received"
      ─▶ WebSocket sos.created ─▶ dashboard toast + command centre + police workspace
Admin/officer: ACKNOWLEDGE ─▶ ASSIGN (admin) / ACCEPT (officer) ─▶ RESPONDING ─▶ RESOLVE (outcome + notes)
      each step: timeline event, audit log, tourist notification + push, WebSocket sos.updated
Tourist app: Emergency status screen polls every 10 s and shows the progress steps and timeline.
```

| Guarantee | How |
|---|---|
| Never shown as sent without server confirmation | the app navigates to the status screen only after a 2xx with `server_confirmed: true`; otherwise shows "Retry" and "Call 112" |
| No duplicates on retry | the same `idempotency_key` is reused for retries; the server returns the original alert (`created: false`) |
| Never auto-resolved | `/status` refuses `RESOLVED`; `/resolve` requires an outcome (`ASSISTED`, `FALSE_ALARM`, `REFERRED`, `UNREACHABLE`, `OTHER`) and ≥3 characters of notes from a staff user |
| Valid transitions only | `OPEN→ACKNOWLEDGED|RESPONDING|RESOLVED|CANCELLED`, `ACKNOWLEDGED→RESPONDING|RESOLVED`, `RESPONDING→RESOLVED`; anything else is HTTP 409 |
| Tourist cancel | only while `OPEN` (not yet acknowledged) |
| Officer isolation | police see unassigned alerts and their own; another officer's case is 403 |
| Provider failure | email/push failures are retried 3× and logged as `FAILED`; the SOS itself is always stored |
| Status after resolution | the tourist's status is re-derived from the last position and zones, not assumed "safe" |
