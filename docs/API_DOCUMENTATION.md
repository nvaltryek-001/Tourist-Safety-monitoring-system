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

## Added in v3 (facilities, datasets, weather, CRUD)
| Area | Endpoints |
|---|---|
| Facilities | `GET /api/v1/facilities` (type=POLICE,HOSPITAL,…, search, district, active, bbox south/west/north/east, page) · `GET /api/v1/facilities/nearby?lat&lon&type&radius_m&limit` · `GET /api/v1/facilities/stats` · `GET /api/v1/facilities/{id}` · `POST /api/v1/facilities` (admin) · `PATCH /api/v1/facilities/{id}` (admin) · `DELETE /api/v1/facilities/{id}` (admin) · `POST /api/v1/facilities/import-dataset` (admin; upserts OSM facilities by OSM id) |
| Nearest help | `GET /api/v1/me/nearby-help[?lat&lon]` (nearest police / hospital / fire station + 15 km list) · `GET /api/v1/sos/{id}/nearest-help` (staff) |
| Datasets | `GET /api/v1/datasets` (manifest + available layers, staff) · `GET /api/v1/datasets/analysis` (staff) · `GET /api/v1/datasets/layers/{districts|protected_areas|attractions|facilities|natural_hazards|district_risk}` (public GeoJSON, open data only) |
| Weather | `GET /api/v1/weather?lat&lon` → Open-Meteo current conditions + rule-based `weather_risk_level` (15-min cache; `available:false` when offline) |
| Tourists (admin) | `PATCH /api/v1/admin/tourists/{code}` · `DELETE /api/v1/admin/tourists/{code}?confirm={code}` (super admin; keeps SOS records, refuses while an SOS is active) |
| Access & staff | `DELETE /api/v1/admin/tourist-access/{id}` · `DELETE /api/v1/admin/staff/{id}` (super admin for admin accounts; not self; not with active incidents) |
| Zones | new fields `category`, `evidence` on create/update/read |

### CRUD coverage
| Resource | Create | Read | Update | Delete |
|---|---|---|---|---|
| Tourists | ✅ | ✅ | ✅ | ✅ (super admin) |
| Tourist login access | ✅ | ✅ | ✅ enable/disable | ✅ |
| Staff / officers | ✅ | ✅ | ✅ | ✅ |
| Safety zones | ✅ (+ import) | ✅ (+ export) | ✅ | ✅ soft / permanent |
| Emergency facilities | ✅ (+ dataset import) | ✅ | ✅ | ✅ |
| SOS incidents | ✅ | ✅ | ✅ lifecycle | — (kept for audit) |
| Trips | ✅ | ✅ | ✅ end | — |
| Location history | ✅ | ✅ | — | ✅ (tourist self / retention purge) |
| Notifications | system | ✅ | ✅ read | — |

## Operational analytics (v3.1)
| Endpoint | Access | Returns |
|---|---|---|
| `GET /api/v1/analytics/hotspots?days&cell_m&min_count&include_zone_entries` | staff | 500 m grid-density cells over SafeTrail's own SOS alerts and restricted-zone entries; `INSUFFICIENT_DATA` below 5 located events |
| `GET /api/v1/analytics/response-times?days` | staff | median and p90 minutes to acknowledge and resolve, by alert type and officer, plus outcome counts |
| `GET /api/v1/analytics/zone-activity?days` | staff | per-zone entries, exits, unique tourists, median dwell time, tourists currently inside |
| `GET /api/v1/analytics/movement?hours` | admin | per-tourist points, distance, stationary minutes, route-deviation flag |
