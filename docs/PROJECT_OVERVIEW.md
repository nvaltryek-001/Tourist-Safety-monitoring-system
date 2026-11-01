# Project overview

**SafeTrail — Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform** is a software-only system that lets tourists share their phone location with consent, warns them about restricted or high-risk zones, lets them raise an SOS, and gives administrators and police officers a live command console to respond.

## Components
| Component | Technology | Folder |
|---|---|---|
| Tourist Android app | Expo (React Native, TypeScript, Expo Router) | `mobile/` |
| Backend API | FastAPI, SQLAlchemy 2, PyJWT | `backend/` |
| Admin & police dashboard | Next.js 15, Tailwind, Leaflet + OpenStreetMap, Recharts | `dashboard/` |
| Database | SQLite locally (existing `tourist_safety.db`), PostgreSQL in production | — |
| Safety intelligence | Explainable rule engine + robust statistics (pure Python) | `backend/app/services/intelligence.py` |
| Notifications | In-app, Expo push, Brevo / Resend / SMTP email | `backend/app/services/notifications.py` |

## What existed before this work
FastAPI app with tourist registration/listing, location update with radius geofence, safety-zone create/list, SOS create/list with dry-run Resend/Twilio code, a `/register` HTML page, Haversine distance, SQLite models (tourists, safety_zones, sos_alerts, tourist_access), KML analysis scripts, a synthetic zone seeder and five tests. There was no mobile app, dashboard, authentication or role model, and the IoT band listed in the old README had no code.

## What was added
See [FINAL_COMPLETION_REPORT.md](FINAL_COMPLETION_REPORT.md) for the full inventory.

## Hardware
None. Location comes only from the phone's GPS and SOS is a software button. The old README's "IoT safety band" module has been removed from the scope; no hardware code existed in the repository, so nothing had to be deleted.
