# SafeTrail — Final Release Audit

Date: 2026-11-02 · Branch: `main` · Audited commit: `046e78e` (fixes in `6bc5167` + `046e78e`)
Statuses used: **PASS**, **FAIL**, **BLOCKED**, **NOT TESTED**. No completion percentage is given.

Evidence for every PASS below is a GitHub Actions run on `main`
([CI workflow](https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system/actions/workflows/ci.yml)),
using isolated in-memory or temporary SQLite databases and test accounts. No real tourist data, real email,
emergency service or real Google key was used.

## 1. Audit scope
| Area | Reviewed |
|---|---|
| FastAPI backend (routers, services, deps, bootstrap, config) | yes |
| Next.js admin dashboard + police workspace | yes |
| Expo mobile app (config, screens, location, queue, SOS) | yes (code + CI; no device) |
| Models, migrations (schema v3), backup/restore | yes |
| Auth/authorization, OTP, sessions, rate limits | yes |
| GPS tracking, geofencing, SOS lifecycle, notifications | yes |
| Google Maps / Leaflet GIS | code review + unit tests; live keys unavailable |
| Dataset pipeline and analytics | yes, numbers recomputed from `datasets/processed/processing_report.json` |
| Tests, GitHub Actions, render.yaml, Dockerfile, docs, README | yes |

The sandbox used for this audit cannot reach npm/PyPI, so full test suites were run in GitHub Actions. Locally only `test_pure_logic.py` (29 passed), `py_compile` of all backend modules and YAML parsing were run.

## 2. Features verified (automated, CI)
| # | Workflow | Status | Evidence |
|---|---|---|---|
| 1 | Admin login / logout | PASS | `test_auth_api.py` |
| 2 | Police login and role-based access | PASS | `test_auth_api.py`, `test_sos_api.py` (police case isolation) |
| 3 | Tourist Gmail approval (allow-list) | PASS | `test_auth_api.py`, `test_tourist_registration.py` |
| 4 | OTP generation | PASS | `test_auth_api.py` (dev echo) |
| 4b | OTP delivery to a real inbox | BLOCKED | needs Brevo/Resend/SMTP credentials |
| 5 | OTP expiry, reuse prevention, attempt limit | PASS | `test_auth_api.py` |
| 6 | Approved tourist login | PASS | `test_auth_api.py` |
| 7 | Location updates via API | PASS | `test_tracking_api.py` |
| 7b | GPS permissions / real GPS on phone | BLOCKED | needs a physical Android device |
| 8 | Location consent and revocation | PASS | `test_tracking_api.py` |
| 9 | Circle geofencing | PASS | `test_pure_logic.py`, `test_zones_api.py` |
| 10 | Polygon geofencing | PASS | `test_pure_logic.py`, `test_zones_api.py` |
| 11 | Zone entry / exit events | PASS | `test_tracking_api.py` |
| 12 | Restricted-zone warnings | PASS | `test_tracking_api.py` |
| 13 | Nearby police stations / hospitals | PASS | `test_geo_api.py` (incl. real-dataset integration test) |
| 14 | SOS creation and duplicate prevention | PASS | `test_sos_api.py` |
| 15 | Admin acknowledgement + officer assignment | PASS | `test_sos_api.py` |
| 16 | Police acceptance and response | PASS | `test_sos_api.py` |
| 17 | Police resolution with notes | PASS | `test_sos_api.py` |
| 18 | Tourist SOS status updates | PASS | `test_sos_api.py` |
| 19 | WebSocket auth / events | PASS | `test_platform_api.py` (first-message auth, 4401 on bad token) |
| 19b | WebSocket reconnect in a real browser over a flaky network | NOT TESTED | reconnect logic is in `dashboard/src/lib/hooks.ts`, no browser E2E |
| 20 | CSV exports and audit logs | PASS | `test_platform_api.py`, `test_geo_api.py` |
| 21 | Dashboard analytics endpoints | PASS | `test_platform_api.py` |
| 21b | Dashboard pages rendered in a browser | NOT TESTED | build + typecheck + lint pass; no browser E2E suite |
| 22 | Database backup and restore (SQLite) | PASS | new `test_backup_script_creates_restorable_sqlite_copy`, `test_restore_replaces_db_and_keeps_safety_copy`, migration v1→v3 test |
| 22b | PostgreSQL `pg_dump` backup | NOT TESTED | no Postgres in CI |
| — | Performance smoke | PASS | 300 location updates 9.2 ms avg; 20 SOS 12.1 ms avg (in-process, CI runner) |

## 3. Bugs found
| # | Severity | Bug |
|---|---|---|
| 1 | HIGH | WebSocket JWT sent as `?token=` in the URL (leaks into proxy/access logs, history) |
| 2 | HIGH | Demo staff passwords hard-coded in `bootstrap.py` and published in README |
| 3 | MEDIUM | `X-Forwarded-For` trusted unconditionally (leftmost entry) → per-IP OTP/login rate limits bypassable by rotating the header; uvicorn ran with `--forwarded-allow-ips="*"` |
| 4 | MEDIUM | Stale facility counts (7,664 / 374 police …, pre-deduplication) in `datasets/README.md` and `FINAL_COMPLETION_REPORT.md` |
| 5 | MEDIUM | `react-native@0.81.4` while Expo SDK 54 expects `0.81.5` (found by the new `expo install --check` step) |
| 6 | LOW | README test badges were static images, not linked to CI |
| 7 | LOW | No Expo dependency diagnostics in CI |
| 8 | LOW | Backup/restore helpers had no direct test |

No CRITICAL bugs were found.

## 4. Bugs fixed
| # | Status | Fix |
|---|---|---|
| 1 | PASS | token sent as first `{"type":"auth","token":…}` message within 10 s; closes 4401 otherwise; token in URL ignored (`operations.py`, `dashboard/src/lib/api.ts`, `hooks.ts`) |
| 2 | PASS | passwords from `DEMO_*_PASSWORD` or randomly generated into git-ignored `backend/demo_credentials.txt`; README table removed; `python -m app.scripts.set_password <email>` added |
| 3 | PASS | `TRUST_PROXY_HEADERS` (default `false`, `true` in render.yaml); rightmost entry only; proxy flags removed from Dockerfile/render start command |
| 4 | PASS | counts corrected to 7,604 (366 / 3,583 / 2,334 / 63 / 1,258, 60 duplicates removed) |
| 5 | PASS | `mobile/package.json` → `react-native 0.81.5`; check now reports "dependencies match the Expo SDK" |
| 6 | PASS | README badges point to `ci.yml`, `datasets.yml`, `uptime.yml` |
| 7 | PASS | `expo install --check` step in mobile CI job (fails the job on mismatch) |
| 8 | PASS | two backup/restore tests added |

Remaining open bugs: none known in repository code. Open items are environmental (section 12).

## 5. Tests executed
| Suite | Command (in CI) |
|---|---|
| Backend | `pytest -q` in `backend/` (+ `ruff check`) |
| Dashboard | `npm run lint`, `npm run typecheck`, `npm test` (vitest), `npm run build` |
| Mobile | `npx expo install --check`, `npm run typecheck`, `npm test` (vitest) |
| Local sandbox | `python3 -m pytest -q backend/tests/test_pure_logic.py`, `python3 -m py_compile backend/app/**/*.py backend/tests/*.py` |

## 6. Exact test results
| Check | Commit | Result |
|---|---|---|
| Backend tests | `046e78e` | PASS — 103 passed, 1 skipped, 66 warnings |
| Dashboard lint / typecheck / tests / build | `046e78e` | PASS |
| Mobile expo check / typecheck / tests | `046e78e` | PASS |
| Mobile expo check | `6bc5167` | FAIL — react-native 0.81.4 vs 0.81.5 (fixed in `046e78e`) |
| Local pure-logic tests | working tree | PASS — 29 passed |

Notes, not hidden:
* The 1 skip is `test_health_api.py`, a smoke test against a *running* server (`API_BASE_URL`); none runs in CI.
* The 66 warnings are library deprecations: `StarletteDeprecationWarning` (httpx test client) and Python 3.12's sqlite3 default datetime adapter (via SQLAlchemy). Neither reflects an application bug; they should be revisited when upgrading Starlette/SQLAlchemy.
* Android build (`eas build`): NOT TESTED (needs an Expo account).

## 7. Security findings
| Check | Status |
|---|---|
| Role-based access / unauthorized access (401/403) | PASS |
| Invalid / expired / revoked tokens | PASS |
| Password hashing (PBKDF2-SHA256), OTP stored as HMAC | PASS (code review + tests) |
| OTP brute force (5 attempts) and rate limits | PASS |
| Rate limit bypass via forged `X-Forwarded-For` | PASS after fix #3 |
| WebSocket token exposure | PASS after fix #1 |
| CORS explicit origins, no credentials | PASS (code review) |
| Input validation / upload limits / KML DTD rejection | PASS |
| SQL injection (ORM, bound params) | PASS (code review) |
| Sensitive data in logs / CSV tourist export without contacts | PASS |
| Secrets in repository files | PASS — diff and tree scanned; no keys, `.env`, DB files or backups committed |
| Secrets in Git history | FAIL (low impact) — old demo passwords remain in history before `6bc5167`; they only work on databases seeded by older versions. Reset with `set_password` |
| Dependency vulnerability scan (`pip-audit`, `npm audit`) | NOT TESTED |
| Staff 2FA | NOT TESTED (feature not implemented) |

Details: [SECURITY_AUDIT.md](SECURITY_AUDIT.md).

## 8. Dataset validation
Recomputed from `datasets/processed/processing_report.json` and processed files.

| Item | Value | Status |
|---|---|---|
| Emergency facilities | 7,604 (POLICE 366, HOSPITAL 3,583, CLINIC 2,334, FIRE_STATION 63, PHARMACY 1,258) | PASS |
| Duplicates removed (same type + name within 100 m) | 60, listed in `facility_duplicates_removed.csv` | PASS |
| Attractions | 283 | PASS |
| Protected areas | 59 (3 unusable geometries) | PASS |
| Natural hazards | 204 (65 waterfalls, 139 cliffs) | PASS |
| District boundaries | 30 (geoBoundaries 2021; Vijayanagara inside Ballari) | PASS |
| Rainfall / weather | Open-Meteo 21,930 district-days; KSNDMC annual series 2020–2025 | PASS |
| Crime records | Karnataka State Police: 179,389 (2022) → 201,733 (2025) | PASS |
| README / manifest / analysis report consistency | stale 7,664 figures fixed in two files | PASS after fix #4 |
| Sources | 42/42 downloaded by the dataset workflow; 37/37 outputs | PASS |
| NCRB, India Tourism statistics, IMD gridded data | not downloaded; marked `NOT_DOWNLOADED` in the manifest | BLOCKED (not openly downloadable) |

Real source data lives in `datasets/raw/`, processed real data in `datasets/processed/` and `application_data/`, and generated test data only in `datasets/synthetic_test_data/` (flagged `synthetic: true` in the app).

## 9. Mobile testing status
| Item | Status |
|---|---|
| TypeScript, unit tests (queue, status, nearby, URL logic) | PASS |
| Expo SDK dependency check | PASS |
| Android APK / EAS build | NOT TESTED |
| Expo Go on a phone: login, OTP, consent, GPS, background tracking, offline queue replay, SOS confirmation, push notifications, battery | BLOCKED — physical device required |

## 10. Google Maps testing status
| Item | Status |
|---|---|
| Key detection and Leaflet/OSM fallback logic | PASS (unit tests) |
| Geometry helpers (paths, holes, bounds, hotspot cells, directions URL) | PASS (unit tests) |
| GeoJSON / KML import-export, invalid coordinates, overlap detection | PASS (backend tests) |
| Live Google Maps web (markers, clustering, circles, polygons, layers, routes) | BLOCKED — needs `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` |
| Android Google Maps | BLOCKED — needs `GOOGLE_MAPS_ANDROID_API_KEY` and a device |

Setup steps: [GOOGLE_MAPS_SETUP.md](GOOGLE_MAPS_SETUP.md). No keys are in the repository.

## 11. Deployment readiness
| Item | Status |
|---|---|
| `render.yaml` (web + Postgres, `TRUST_PROXY_HEADERS`) parses | PASS |
| Dashboard production build | PASS |
| Production start refuses dev/short `SECRET_KEY` | PASS (`test_production_refuses_dev_or_short_secret_key`) |
| Live Render / Vercel deployment | BLOCKED — not deployed in this audit (needs account approval) |
| Real email delivery in production | BLOCKED — needs Brevo/Resend key |

## 12. Remaining blockers
1. Physical Android testing (Expo Go or APK): GPS, background tracking, offline queue, push, SOS on device.
2. Google Maps keys (web + Android) for live map testing.
3. Email provider key for real OTP delivery.
4. Render/Vercel deployment and a post-deploy smoke run (`API_BASE_URL=… pytest tests/test_health_api.py`).
5. Existing local databases (yours and your friend's) may still hold the old published demo passwords — run `python -m app.scripts.set_password <email>` for each demo account.
6. `pip-audit` / `npm audit` not run.

## 13. Final release decision
**READY WITH LIMITATIONS.**

Every automated check on `main` (`046e78e`) passes, and all bugs found in the repository code are fixed and covered by tests. The release is not "ready for demonstration" without qualification because the parts a reviewer will actually see on a phone or a live map (device GPS, Android build, Google Maps, real OTP email, the deployed site) have not been tested; they are BLOCKED on hardware and credentials, not on known code defects.
