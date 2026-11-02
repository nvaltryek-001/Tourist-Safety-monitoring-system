# Testing report

All results below are from GitHub Actions (`.github/workflows/ci.yml`, Ubuntu, Python 3.12, Node 20) on branch `feature/complete-tourist-safety-platform`, commit `8be1084`, 2026-11-01. Nothing is reported that did not run.

| Suite | Command | Result |
|---|---|---|
| Backend lint | `ruff check app tests --select E9,F` | ✅ pass |
| Backend tests | `pytest -q` | ✅ **82 passed, 1 skipped**, 0 failed |
| Dashboard lint | `next lint` | ✅ pass |
| Dashboard types | `tsc --noEmit` (strict) | ✅ pass |
| Dashboard unit tests | `vitest run` | ✅ 1 file, 6 tests passed |
| Dashboard production build | `next build` | ✅ pass |
| Mobile types | `tsc --noEmit` (strict, Expo SDK 54 types) | ✅ pass |
| Mobile unit tests | `vitest run` | ✅ 1 file, 8 tests passed |

The skipped test is `test_health_api.py::test_live_health_endpoint`, which only runs when a server is reachable at `SMART_TOURIST_API_URL`.

## Backend coverage by requirement
| Requirement | Tests |
|---|---|
| Startup, health, readiness | `test_health_and_ready` |
| Tourist registration (legacy + v1), duplicates | `test_tourist_registration.py`, `test_register_tourist_*` |
| Existing tourist login / invalid login | `test_tourist_otp_login_flow`, `test_non_gmail_and_unapproved_rejected`, `test_wrong_and_reused_otp`, `test_gmail_dot_variant_matches_same_account` |
| OTP honesty, rate limiting | `test_otp_response_is_honest_about_delivery`, `test_otp_request_rate_limited` |
| Staff auth, lockout, logout, sessions, password change | `test_staff_login_and_lockout`, `test_logout_revokes_token`, `test_session_list_and_revoke_others`, `test_change_password` |
| Authorization boundaries | `test_authorization_boundaries`, `test_only_super_admin_creates_admins`, `test_police_sees_masked_contact_details`, `test_legacy_location_endpoint_requires_owner`, `test_tourist_cannot_read_other_tourist_sos`, `test_police_accept_and_isolation`, `test_police_location_history_only_during_active_sos` |
| GPS updates, invalid coordinates, consent | `test_consent_required_for_location`, `test_invalid_coordinates_rejected`, `test_older_point_does_not_overwrite_latest` |
| Geofence entry/exit + alert | `test_geofence_entry_and_exit` |
| Offline batch de-duplication | `test_offline_batch_deduplicates` |
| Zone CRUD, polygon validation, duplicates, import/export | `test_zones_api.py` (6 tests) |
| SOS create, duplicate (idempotency), acknowledge, assign, resolve, cancel | `test_sos_api.py` (9 tests) |
| Notification failure & provider statuses | `test_notification_provider_failure_is_recorded`, `test_notification_provider_success_is_not_called_delivered` |
| WebSocket updates & auth | `test_websocket_receives_sos_event`, `test_websocket_rejects_bad_token` |
| Migration, data preservation (6/209/5), idempotency, rollback | `test_migration_upgrades_v1_database_without_losing_rows` |
| Analytics & AI | `test_analytics_and_intelligence`, 20 pure-logic tests in `test_pure_logic.py` |
| Performance smoke | `test_location_and_sos_throughput` |

## End-to-end workflow (API level)
`test_geofence_entry_and_exit` + `test_full_incident_lifecycle` together cover: tourist OTP login → consent → GPS upload → restricted-zone entry → tourist alert → SOS → admin sees and acknowledges → officer assigned, responding, resolves with notes → tourist sees `RESOLVED` and receives notifications.

## Performance (in-process smoke, not a load test)
CI, single process, SQLite, TestClient — two runs:
* 300 location updates from 100 tourists: **2.49–2.63 s** total (**8.3–8.8 ms** average)
* 20-alert SOS burst: **0.16–0.23 s** (8.2–11.3 ms average)
* Overview analytics: 11–18 ms

These numbers do not include network latency or PostgreSQL and do not prove concurrent capacity. Run `python -m app.scripts.load_test --url <deployed API> --token-file tokens.txt --concurrency 100` for real figures.

## Not automated
Device/UI automation (Detox/Playwright), push delivery to a real phone, email delivery to a real inbox, and background location on a device. These require credentials or hardware and are listed in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## v3 update — maps, datasets, facilities, CRUD (2026-11-02)
GitHub Actions, branch `feature/gis-maps-datasets`, commit `69e7df2`:

| Suite | Result |
|---|---|
| Backend `pytest` | ✅ **92 passed, 1 skipped**, 0 failed |
| Dashboard lint · `tsc` · vitest (10 tests) · `next build` | ✅ pass (Google Maps components compile and build) |
| Mobile `tsc` · vitest (10 tests) | ✅ pass (`PROVIDER_GOOGLE` map, nearby help, server screen) |
| Datasets workflow | ✅ 42/42 sources downloaded, 37/37 processing outputs OK, analysis generated |

New backend tests (`tests/test_geo_api.py`): OSM facility import idempotency, nearest police/hospital search and type filters, facility CRUD and permissions, SOS nearest-help, weather risk rules and offline behaviour, dataset layers and manifest, tourist update/delete safeguards, access and staff delete, zone category/evidence, open-data → pending-review zone import, and **one integration test against the real committed dataset** (more than 5,000 facilities imported, a police station within 3 km of MG Road Bengaluru, 30 district polygons, crime years 2022/2024/2025).

**Not tested here (need your keys or a phone):** Google tiles, Advanced Markers, Directions routes and Android Google rendering. CI proves they compile and build; follow the checklist in [GOOGLE_MAPS_SETUP.md](GOOGLE_MAPS_SETUP.md).

## v3.1 update (2026-11-02, commit `b72ed07`)
Backend **97 passed, 1 skipped, 0 failed**; dashboard lint, types, tests and build pass; mobile types and tests pass. New tests cover hotspot clustering (including the minimum-data refusal), response-time percentiles, zone dwell time, movement summary and the four analytics endpoints with role checks.
