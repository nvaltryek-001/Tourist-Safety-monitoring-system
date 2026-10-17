# Project Plan — Smart Tourist Safety Monitoring & Incident Response System

## 1. Scope and outcome
One integrated college major project with:
1. **Tourist mobile app:** React Native + Expo Go, tourist-only.
2. **Separate admin web dashboard:** operations, response, geography, reports, and historical incident intelligence.
3. **FastAPI backend + existing database:** single source of truth for authorized accounts, tourists, locations, journeys, zones, SOS incidents, notifications, and historical data.
4. **Geographic and historical data pipeline:** source-attributed, validated, reproducible, with raw and normalized data kept separate.

Do not turn this into an SIH project or introduce unrelated systems/frameworks. Preserve the current repository and extend it incrementally.

## 2. Fixed implementation order
**Phase 1 → 2 → 3 → 4 → 5 → 6 → 7.** Do not jump phases unless a verified dependency requires it; document the reason and smallest adjustment first.

### Phase 1 — Close the nine demo-geofence checkpoint
- Verify backend health/startup.
- Verify the nine exact `College Demo Zone 01`–`09` database rows and configuration.
- Verify all nine appear in a fresh `GET /zones` response.
- Report duplicate Zone 01 concern accurately; never delete records without explicit approval.
- Confirm coordinates, 200 m radius, active state, type, and explicit demo disclaimer.
- Do not describe demo zones as legally verified restrictions.
- Save evidence and then proceed.

Planned demo locations:
| Zone | Latitude | Longitude | Radius |
|---|---:|---:|---:|
| College Demo Zone 01 | 13.165771 | 77.558813 | 200 m |
| College Demo Zone 02 | 13.169332 | 77.559002 | 200 m |
| College Demo Zone 03 | 13.169124 | 77.557839 | 200 m |
| College Demo Zone 04 | 13.165915 | 77.557965 | 200 m |
| College Demo Zone 05 | 13.168600 | 77.562516 | 200 m |
| College Demo Zone 06 | 13.167876 | 77.560908 | 200 m |
| College Demo Zone 07 | 13.167569 | 77.559406 | 200 m |
| College Demo Zone 08 | 13.168212 | 77.558325 | 200 m |
| College Demo Zone 09 | 13.168738 | 77.559493 | 200 m |

### Phase 2 — Repository and data audit
Inspect actual tree, source files, configs, tests, DB tables/counts, API routes/schemas, auth, location/journey/SOS/notification models and routes, mobile app, dashboard, geographic files, dependencies and current test failures. Report:
- DONE AND VERIFIED
- PARTIALLY IMPLEMENTED
- NOT IMPLEMENTED
- BLOCKED / NEEDS DECISION

Do not infer implementation from folder names or old notes. Create/maintain `docs/PROJECT_STATUS.md` in the repository after inspecting whether it already exists.

### Phase 3 — Backend and data foundation
Only implement gaps confirmed in Phase 2. Likely capability areas (do not duplicate existing models):
- Approved tourist authentication and secure password hashing/token/session handling.
- Server-side ownership checks and role-based admin authorization.
- Latest location plus location history, timestamp and accuracy.
- Journey create/start/end/status lifecycle.
- SOS unique ID, idempotent submission, status lifecycle and audit history.
- Notification attempt/provider status logging; delivery only when confirmed.
- Zone source and verification metadata; controlled geofence warnings.
- Historical source registry, import jobs, raw source references, normalized records, aggregate statistics stored separately from individual incidents.
- Input validation, indexes, safe migrations, backups, tests.
Use small changes, test each change, and document migrations and rollback/recovery.

### Phase 4 — Tourist mobile app (Expo Go first)
Inspect existing app and SDK before installing or replacing anything. Tourist-only screens and flows:
- Splash, approved college email login, secure session, profile/logout.
- Home and monitoring status.
- Foreground GPS, freshness/accuracy and authenticated uploads.
- Map, route planner and zone polygons with verification labels.
- Journey lifecycle, route distance/ETA from routing provider where configured.
- SOS submission and accurate server status.
- Emergency contacts/quick help, personal safety history, notifications.
- Offline queue/sync status that never implies a queued SOS was delivered.
- Settings/privacy, safety guide, voice/haptics where compatible.
Use actual APIs, explicit loading/error/empty/offline states, and no hardcoded production profiles. Expo Go cannot guarantee tracking while terminated/suspended; state limitations. Speech recognition/background tracking may require a development build; investigate only when justified.

### Phase 5 — Separate admin dashboard
Inspect existing dashboard and select its existing stack if viable. Required connected modules:
- Secure login and backend-enforced role permissions.
- Operations metrics from actual data, not placeholders.
- Tourist search/list and timestamped map with stale-location state.
- SOS command centre with status workflow, incident timeline and audit.
- Journeys and location history.
- Zone/polygon explorer separating demo, pending review and verified data.
- Notification logs with accurate provider statuses.
- Historical Incident Intelligence section (detailed below).
- Data import/validation history, reports/authorized exports, admin settings and audit logs.
Map provider, tile/data license and API key handling must be documented. No secrets in frontend.

### Phase 6 — Historical Karnataka Incident Intelligence (mandatory)
**First task after current geofence checkpoint and Phase 2 audit:** identify candidate datasets, confirm actual download format/coverage/licensing and produce a source inventory before importing or displaying statistics.

Candidate sources to investigate (not yet confirmed downloaded):
- Karnataka Police accident reports/district-level statistics.
- Karnataka government data portal and relevant crime/disaster datasets.
- Government of India road-accident statistics and data.gov.in.
- OpenCity Karnataka road-accident dataset.
- Official disaster-management records where suitable.

For every source, record publisher, title, URL, publication date, event coverage years, license/usage conditions, format, geography granularity, categories, acquisition date, raw file checksum if feasible, and review status.

Data pipeline:
1. Acquire actual source files only when accessible and permitted.
2. Preserve unmodified raw copy.
3. Inspect schema, coverage, geographic granularity and license.
4. Normalize to a separate dataset; never silently overwrite raw files.
5. Validate types, dates, counts, coordinates and categories; detect duplicates and missing values.
6. Preserve source row/record ID and provenance.
7. Distinguish individual incident events from district/state aggregate counts; store them separately.
8. Mark uncertain or approximate locations and verification state.
9. Produce a data-quality report and reconcile totals to source.
10. Only then enable production charts/maps.

Dashboard section: **Historical Incident Intelligence**
1. Dataset Management: imports, source metadata, coverage, validation errors and review status.
2. Analytics Dashboard: yearly trends, district comparisons, category breakdown, supported monthly/seasonal patterns, injuries/fatalities where provided, coverage/missingness.
3. Historical Incident Map: Karnataka/district overview; event points only where reliable coordinates exist; aggregate choropleth only with appropriate district boundaries; heatmaps only with defensible point-level data.
4. Record Explorer: search/filter, record details, provenance and verification state.
5. Route/District Comparison: compare supported historical counts with clear coverage caveats; do not imply a calibrated risk score unless valid exposure data supports it.

Filters: year range, district, category, source, verification state, geographic granularity.
Exports: only authorized and permitted data; preserve provenance and disclose limitations.
Charts: use real validated data. Clearly label any temporary mock display “ILLUSTRATIVE — NOT REAL INCIDENT DATA.”
Never invent events, statistics, coordinates or source coverage. A district aggregate is not a point location. Higher recorded counts do not prove higher underlying risk without exposure/reporting context. Separate historical incidents from live SOS.

### Phase 7 — Integration, acceptance tests and handoff
Test complete tourist → backend → dashboard flow:
- Approved tourist logs in and gets own profile.
- Foreground GPS updates persist with timestamps/accuracy.
- Dashboard shows last-known position and freshness, not falsely “live”.
- Journey starts and appears in dashboard.
- SOS creates unique incident; dashboard acknowledges/updates it.
- Notification attempts/provider responses are recorded accurately.
- Zone warnings use correct data status and cooldown/deduplication.
- Historical data imports reconcile and charts match source.
- Test invalid input, unauthorized requests, stale GPS, network outage, retry/idempotency and empty data.
- Test Expo Go on phone where possible.
- Document setup, environment variables, run commands, test results, limitations and reproducible demo sequence.

## 3. Security and integrity requirements
- Domain allowlisting is not authentication.
- No hardcoded credentials, plain-text passwords, tokens or provider secrets.
- Backend enforces identity, ownership and roles.
- Minimize exposure of personal/emergency contact data.
- Never send real SOS messages to emergency contacts/services during tests without explicit authorization.
- Preserve existing data; backup before schema changes/destructive operations.
- Never delete/merge duplicate zones or records without inspection and approval.
- No claim of completion without verification.

## 4. Development cadence
Each task response must state:
**Current phase / Goal / Action / Expected result / Verification / Checklist update.**
Give one main task at a time. Commands should be PowerShell-compatible, identify working directory and whether a second terminal is needed. Wait for output if it affects the next step. On error: diagnose from complete output, make smallest safe fix, rerun relevant test. Avoid giant untested scripts and unnecessary rewrites.

## 5. Definition of done
A feature is complete only when implemented in the actual project, connected to real backend/source data where required, tested against its acceptance criteria, and documented. A created folder or written code alone is not enough.
