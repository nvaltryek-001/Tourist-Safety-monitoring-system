# Decisions Log

## D-001 — One integrated project
**Decision:** Tourist Expo Go app, separate admin dashboard, existing FastAPI backend, and historical/geographic pipeline are one project with one backend/database source of truth.
**Reason:** Preserve the scope in the user-supplied master prompts.
**Status:** Fixed.

## D-002 — Implementation order
**Decision:** Demo geofence verification → repository audit → backend foundation → tourist app → admin dashboard → historical intelligence → end-to-end testing.
**Status:** Fixed unless a verified dependency requires a documented small adjustment.

## D-003 — Historical-data integrity
**Decision:** Keep raw files and normalized files separate; individual incidents and aggregate statistics are different record types; preserve provenance, coverage and verification status; no fabricated values or coordinates.
**Status:** Fixed.

## D-004 — Geographic trust
**Decision:** College demo zones and synthetic `DEMO-KA-*` records must be labelled synthetic/demo. Geographic polygons marked pending review are not legally verified restrictions.
**Status:** Fixed.

## D-005 — Zone cleanup
**Decision:** Do not delete or merge Zone 01 duplicates without inspecting current data and explicit user approval.
**Status:** Await current full API/database comparison.

## D-006 — Expo Go limitations
**Decision:** Prioritize foreground location in Expo Go. Do not promise reliable terminated/background tracking. Any development-build-only feature requires an explicit feasibility check.
**Status:** Fixed.

## D-007 — Unknown data-source facts
**Decision:** Candidate URLs are research leads, not proof of an acquired dataset, coverage years, license or format.
**Status:** Fixed.

## D-008 — Work cadence
**Decision:** One main task at a time; PowerShell-first; user returns output; use smallest safe changes; mark checklist only after verification.
**Status:** Fixed.

## D-009 — Phase 1 API evidence (2026-10-17)
**Decision/status:** Live health and zone API checks are verified. All nine expected demo zones are returned. Exact name + coordinate duplicates were not found in the API response. A broader coordinate/overlap inventory remains pending; no zone cleanup is authorized by this check.
