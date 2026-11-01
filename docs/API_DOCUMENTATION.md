# API documentation

Interactive OpenAPI docs: `GET /docs` (Swagger) and `GET /openapi.json` on the running backend. All `/api/v1` errors return `{"detail": "..."}`; validation errors also include `errors: [{field, message}]`.

## Original endpoints (paths and response shapes kept)
| Method & path | Auth (v2) | Notes |
|---|---|---|
| `GET /` | public | unchanged |
| `GET /health` | public | unchanged; `/ready` adds a DB check |
| `POST /tourists` | **admin** | was public — exposed personal data |
| `GET /tourists` | **admin** | was public — listed phones/emails |
| `POST /tourists/{code}/location` | that tourist or staff | adds `geofence_events` to the response |
| `GET /zones` | public | unchanged (zones are not personal data) |
| `POST /zones` | **admin** | |
| `POST /tourists/{code}/sos` | that tourist or staff | `notification_results` now use honest statuses (`NOT_CONFIGURED`, `ACCEPTED_BY_PROVIDER`, `FAILED`, …) |
| `GET /sos` | staff | was public |
| `GET /register` | public page | now signs in as admin before registering |

## v1 API
| Area | Endpoints |
|---|---|
| Auth | `POST /api/v1/auth/tourist/request-otp`, `POST /api/v1/auth/tourist/verify-otp`, `POST /api/v1/auth/staff/login`, `POST /api/v1/auth/staff/change-password`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/sessions`, `POST /api/v1/auth/sessions/{id}/revoke`, `POST /api/v1/auth/sessions/revoke-others` |
| Tourist self | `GET/PATCH /api/v1/me`, `POST /api/v1/me/consent`, `POST /api/v1/me/location`, `POST /api/v1/me/locations/batch`, `GET/DELETE /api/v1/me/locations`, `GET /api/v1/me/status`, `POST/GET /api/v1/me/sos`, `GET /api/v1/me/sos/{id}`, `POST /api/v1/me/sos/{id}/cancel`, `GET/POST /api/v1/me/trips`, `POST /api/v1/me/trips/{id}/end`, `GET /api/v1/me/notifications`, `POST /api/v1/me/notifications/{id}/read`, `GET /api/v1/me/safety-report` |
| Zones | `GET /api/v1/zones` (search, zone_type, active, synthetic), `GET /api/v1/zones/{id}`, `POST`, `PATCH /{id}`, `DELETE /{id}?confirm_name=&permanent=`, `POST /import` (multipart, `dry_run`, `activate`), `GET /export?format=geojson|kml`, `GET /overlaps`, `GET /audit`, `POST /check` |
| SOS (staff) | `GET /api/v1/sos` (status, scope=all|mine|active, near_lat/near_lon), `GET /{id}`, `POST /{id}/acknowledge`, `/accept` (police), `/assign` (admin), `/status`, `/resolve` (outcome + notes), `/notes` |
| Admin | `GET/POST /api/v1/admin/tourists`, `GET /api/v1/admin/tourists/{code}`, `GET /api/v1/admin/tourists/{code}/locations`, `GET/POST/PATCH /api/v1/admin/tourist-access`, `GET/POST/PATCH /api/v1/admin/staff`, `GET /api/v1/admin/officers`, `GET /api/v1/admin/audit-logs`, `GET /api/v1/admin/data-audit`, `POST /api/v1/admin/retention/purge` |
| Analytics & AI | `GET /api/v1/analytics/overview`, `GET /api/v1/analytics/trends?days=`, `GET /api/v1/intelligence/tourists`, `/zones`, `/report` |
| Notifications | `GET /api/v1/notifications`, `POST /{id}/read`, `POST /read-all`, `GET /delivery-log` (admin) |
| System | `GET /api/v1/system/health`, `GET /ready`, `GET /api/v1/system/info` (admin) |
| Real-time | `WS /ws?token=<jwt>` → `{type, data}` events: `hello`, `location.updated`, `geofence.event`, `sos.created`, `sos.updated`, `pong` |

Pagination (`page`, `page_size`) returns `{items, total, page, page_size}` on tourist and audit lists.
