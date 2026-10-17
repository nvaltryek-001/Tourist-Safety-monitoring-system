# Acceptance Tests

## Phase 1: Demo zones
- [ ] Backend starts without traceback.
- [ ] `/health` responds successfully.
- [ ] DB query shows exactly the nine intended names and expected coordinates.
- [ ] Fresh `GET /zones` contains all nine.
- [ ] Every intended zone has 200 m radius, `RESTRICTED`, active status, demo disclaimer.
- [ ] Full zone list inspected for name/coordinate duplicates.
- [ ] No data changed during verification.

## Backend security and workflows
- [ ] Invalid credentials rejected.
- [ ] Unapproved tourist cannot log in.
- [ ] Tourist can retrieve only own profile/history/contacts.
- [ ] Admin routes require authentication and correct role.
- [ ] Location writes are tied to authenticated identity and include timestamp/accuracy when available.
- [ ] Journey state transitions validated.
- [ ] SOS has unique ID/idempotency and status timeline.
- [ ] Notification attempt is distinct from provider acceptance/delivery.
- [ ] Invalid coordinates and malformed payloads rejected.
- [ ] Tests pass from documented command.

## Mobile
- [ ] Expo Go startup and navigation.
- [ ] Login/profile/logout.
- [ ] Foreground GPS permission granted/denied/stale.
- [ ] Authenticated location upload.
- [ ] Zones/polygons correctly labelled.
- [ ] Journey start/end.
- [ ] SOS success/failure/retry and server status.
- [ ] Offline queue never falsely claims delivery.
- [ ] Personal history and privacy.
- [ ] No cross-tourist data access.

## Admin
- [ ] Admin login and role authorization.
- [ ] KPIs reconcile with backend.
- [ ] Tourist list privacy checks.
- [ ] Timestamped locations and stale state.
- [ ] SOS status lifecycle and audit.
- [ ] Zone metadata and pending-review distinction.
- [ ] Notification statuses accurate.
- [ ] Historical dataset import/validation/review.

## Historical data
- [ ] Source inventory records URL, publisher, coverage, format, license, granularity.
- [ ] Raw dataset preserved unchanged.
- [ ] Normalized data separate.
- [ ] Duplicates, missing values, invalid dates/counts/coordinates reported.
- [ ] Individual incidents and aggregate statistics are separated.
- [ ] Charts reconcile with source.
- [ ] Maps do not invent point locations.
- [ ] Missing years/district coverage visible.
- [ ] Source provenance appears in record explorer/export.
- [ ] No mock data appears as real incidents.

## End-to-end
- [ ] Approved tourist login → profile.
- [ ] GPS → backend → admin map.
- [ ] Journey → admin.
- [ ] SOS → admin → authorized status update.
- [ ] Notification provider outcomes accurately shown.
- [ ] Historical dataset → quality report → chart/map.
- [ ] Offline, stale GPS, authorization, retries and errors tested.
- [ ] Reproducible setup and demonstration documented.
