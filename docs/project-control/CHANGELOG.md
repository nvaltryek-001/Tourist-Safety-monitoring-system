# Verified Change Log

## 2026-10-17 — Project control pack created
- Created an external planning pack from the user-provided project prompts and current conversation.
- Recorded the next step as filtering `GET /zones` for the nine college demo zones.
- No project repository or database was changed by creating this pack.
- No historical dataset is claimed to have been downloaded or validated.
- Database and API state notes are based on terminal output shared in the conversation and should be rechecked where indicated.

## 2026-10-17 — Live API verification
- `GET /health` returned `status: healthy`.
- `GET /zones` returned 209 records.
- Filtering the live response returned exactly nine College Demo Zones: IDs 201, 203, 205, 210, 211, 212, 213, 214, 215.
- All nine displayed zones were active, `RESTRICTED`, and configured with a 200 m radius.
- Each expected College Demo Zone name occurred once.
- No duplicate exact `name + latitude + longitude` combinations were found in the API response.
- Limitation: different names at identical coordinates and nearby overlaps have not yet been ruled out.
- No zone records were created, deleted, or modified during these checks.

## 2026-11-01 — Platform completion (v2.0)
- Backend v2: authentication/roles, additive migrations, SOS lifecycle, geofence events, notifications, AI advisories, WebSocket; legacy routes preserved but personal-data routes now require auth.
- New Next.js dashboard (admin + police) and Expo tourist app.
- CI on GitHub Actions: backend 82 passed / 1 skipped; dashboard lint, types, 6 tests, build pass; mobile types and 8 tests pass.
- Real `tourist_safety.db` was not available in the repository; no data was changed. See docs/FINAL_COMPLETION_REPORT.md.
