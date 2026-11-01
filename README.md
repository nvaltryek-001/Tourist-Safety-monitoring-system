 <div align="center">

# 🛡️ SafeTrail

### Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform

**A smarter, safer and more connected tourism ecosystem.**

Real-time tourist tracking · Intelligent geofencing · Emergency SOS · AI safety advisories · Live command centre

<br/>

![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-Dashboard-black?style=for-the-badge&logo=next.js)
![React Native](https://img.shields.io/badge/Expo-Mobile-000020?style=for-the-badge&logo=expo)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178C6?style=for-the-badge&logo=typescript&logoColor=white)

![Software Only](https://img.shields.io/badge/Architecture-100%25%20Software--Only-success?style=flat-square)
![Privacy First](https://img.shields.io/badge/Design-Privacy%20First-blue?style=flat-square)
![Deployment](https://img.shields.io/badge/Deployment-Render%20%7C%20Vercel-7C3AED?style=flat-square)

<br/>

**[Explore Repository](https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system) · [Report an Issue](https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system/issues)**

</div>

---

## 🌍 1. Project Overview

SafeTrail is a full-stack, software-only tourist safety monitoring and incident intelligence platform designed to improve tourist protection through real-time location monitoring, geographical safety intelligence and emergency response management.

The platform connects three major components:

- **Tourist Mobile Application:** Allows tourists to share their location with consent, monitor safety zones and request emergency assistance.
- **Admin Command Centre:** Provides centralized tourist monitoring, geographical zone management, incident management and safety analytics.
- **Police Monitoring Dashboard:** Enables authorized officers to receive, acknowledge, manage and resolve emergency incidents.

SafeTrail combines GPS tracking, geofencing, real-time communication, risk analysis and emergency notifications into one integrated ecosystem.

### 🎯 Project Vision

To build an intelligent digital safety infrastructure that helps tourists travel confidently while enabling authorities to monitor potential risks and respond to emergencies efficiently.

> **No additional hardware is required.** SafeTrail uses smartphone GPS, software-based emergency controls and cloud-connected applications.

---

## ✨ 2. Key Features

### 📱 Tourist Android Application

- Passwordless Gmail authentication using a six-digit OTP.
- Privacy and location-sharing consent.
- Real-time smartphone GPS tracking.
- Location accuracy and update status.
- Offline location queue and synchronization.
- Interactive safety map.
- Restricted-zone and high-risk area warnings.
- Tourist safety status monitoring.
- One-touch, hold-to-confirm SOS.
- Emergency status tracking.
- Push notifications.
- Travel history.
- Emergency contacts.
- AI-generated safety advisories.

### 🖥️ Admin Command Centre

- Centralized monitoring dashboard.
- Live tourist location visualization.
- Real-time WebSocket updates.
- Tourist registration and management.
- Tourist search and filtering.
- Safety-zone management.
- Geographical dataset management.
- KML and GeoJSON import/export.
- SOS emergency command centre.
- Police officer management.
- Incident assignment and resolution.
- AI safety intelligence.
- Analytics and reporting.
- Audit logs.
- System configuration.

### 🚓 Police Monitoring Dashboard

- Secure officer authentication.
- Assigned emergency incidents.
- Nearby unassigned SOS alerts.
- Tourist location visualization.
- Emergency acknowledgement.
- Incident response management.
- Incident notes and timelines.
- Google Maps navigation links.
- Controlled access to tourist contact information.

### 🧠 AI-Based Safety Intelligence

- Prolonged stationary movement detection.
- Unusual route deviation analysis.
- High-risk zone detection.
- Repeated restricted-zone entry detection.
- Tourist risk scoring.
- Geographical risk ranking.
- Incident trend analysis.
- Explainable safety advisories.

AI results are advisory indicators, not automatic confirmation of emergencies.

---

## 🏗️ 3. System Architecture

SafeTrail follows a centralized full-stack architecture.

```text
                  SAFETRAIL ECOSYSTEM
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
    TOURIST APP       ADMIN PANEL      POLICE PANEL
    React Native       Next.js           Next.js
       Expo           Dashboard         Dashboard
          |                |                |
          +----------------+----------------+
                           |
                           v
                    FASTAPI BACKEND
                           |
       +-------------------+-------------------+
       |          |          |          |       |
       v          v          v          v       v
     AUTH       GPS       GEOFENCE     SOS     AI ENGINE
       |          |          |          |       |
       +----------+----------+----------+-------+
                           |
                           v
                     DATABASE
                  SQLite / PostgreSQL
                           |
                           v
                 REAL-TIME UPDATES
                  WebSocket / Push
```

### Architecture Principles

- One centralized backend.
- One shared database.
- Role-based access control.
- Secure API communication.
- Consent-based location sharing.
- Modular services.
- Scalable deployment architecture.
- No hardware dependency.

---

## 🧰 4. Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI |
| ORM | SQLAlchemy |
| Authentication | JWT, OTP |
| Database | SQLite, PostgreSQL |
| Geospatial | GeoJSON, KML, Shapely |
| Admin Dashboard | Next.js 15, React |
| Frontend Language | TypeScript |
| Styling | Tailwind CSS |
| Mapping | Leaflet, OpenStreetMap |
| Charts | Recharts |
| Mobile | React Native, Expo |
| Mobile Navigation | Expo Router |
| Mobile GPS | Expo Location |
| Real-time | WebSocket |
| Email | Brevo / Resend / SMTP |
| Push Notifications | Expo Push Notifications |
| Testing | Pytest, Vitest |
| CI/CD | GitHub Actions |
| Backend Hosting | Render |
| Dashboard Hosting | Vercel |
| Android Builds | Expo EAS |

---

## 📍 5. Geographical Safety Dataset

Geographical data is a core component of SafeTrail.

The platform supports safety-zone management and geographical monitoring using structured geographical records.

### Existing Dataset Inventory

| Dataset | Previously recorded count |
|---|---:|
| Karnataka demonstration zones (`DEMO-KA`) | 200 |
| SVIT College demonstration zones | 9 |
| Total reported safety zones | 209 |
| Registered tourists | 6 |
| Historical SOS records | 5 |

**Important dataset information:**

- The 200 `DEMO-KA` records are synthetic demonstration zones.
- The nine SVIT zones are college demonstration records.
- The original geographical KML dataset has not yet been independently verified.
- The nine SVIT zones were previously reported with a 200-metre radius. A later 50-metre specification remains to be verified and applied.
- The private SQLite database is not included in the public repository.

### Geographical Capabilities

- Zone visualization.
- Restricted-area detection.
- Polygon validation.
- Radius-based geofencing.
- Duplicate detection.
- Overlap analysis.
- KML import/export.
- GeoJSON import/export.
- Zone management.
- Geographical safety analytics.

The platform is designed to support additional verified geographical datasets without replacing existing records.

---

## 🚨 6. Emergency SOS Workflow

Emergency response is one of the primary functions of SafeTrail.

```text
Tourist presses SOS
        |
        v
Mobile obtains latest location
        |
        v
Backend receives SOS request
        |
        v
Unique emergency alert created
        |
        v
Admin dashboard receives alert
        |
        v
Authorized officer acknowledges
        |
        v
Officer responds to incident
        |
        v
Incident resolution
        |
        v
Tourist receives status update
```

### SOS Status Lifecycle

| Status | Description |
|---|---|
| OPEN | Emergency request received |
| ACKNOWLEDGED | Alert acknowledged |
| RESPONDING | Officer responding |
| RESOLVED | Incident resolved |

Each incident supports timestamps, assignment details, response notes and an incident timeline.

---

## 🔐 7. Authentication and Security

SafeTrail supports separate authentication workflows for tourists and staff.

### Tourist Authentication

- Gmail-only identity.
- Approved tourist email addresses.
- Six-digit OTP verification.
- OTP expiration.
- One-time token usage.
- Secure session handling.

### Staff Authentication

- Super Admin.
- Admin.
- Police Officer.

Staff authentication uses protected credentials and role-based permissions.

### Security Features

- Password hashing.
- JWT-based authentication.
- Rate limiting.
- Login protection.
- Session revocation.
- Protected API endpoints.
- Role-based authorization.
- Privacy-aware location access.
- Audit logging.
- Sensitive data protection.

### Privacy Principles

- Location sharing requires consent.
- Tourist information is access-controlled.
- Police access to sensitive contact details is restricted.
- Location history has a configurable retention policy.
- Personal data and secrets must never be committed to GitHub.

---

## 🖥️ 8. Application Modules

| Module | Description |
|---|---|
| Tourist App | Mobile tourist safety application |
| Admin Dashboard | Central management portal |
| Police Dashboard | Emergency response workspace |
| GPS Service | Real-time mobile location tracking |
| Geofencing Engine | Geographical boundary detection |
| SOS Service | Emergency incident management |
| AI Engine | Risk analysis and safety advisories |
| Notification Service | Email and mobile push |
| Dataset Manager | Geographical data management |
| Analytics | Safety and incident reporting |

---

## 📂 9. Repository Structure

```text
Tourist-Safety-monitoring-system/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── scripts/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── migrations/
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── dashboard/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   ├── public/
│   └── package.json
│
├── mobile/
│   ├── app/
│   ├── components/
│   ├── services/
│   ├── hooks/
│   ├── assets/
│   └── package.json
│
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_DESIGN.md
│   ├── API_DOCUMENTATION.md
│   ├── AUTHENTICATION.md
│   ├── GPS_AND_LOCATION.md
│   ├── GEOFENCING.md
│   ├── DATASET_DOCUMENTATION.md
│   ├── SOS_WORKFLOW.md
│   ├── AI_INTELLIGENCE.md
│   ├── SECURITY_AUDIT.md
│   ├── TESTING_REPORT.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── ENVIRONMENT_VARIABLES.md
│   └── FINAL_COMPLETION_REPORT.md
│
├── render.yaml
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 💻 10. Local Installation

### Prerequisites

Install the following:

- Python 3.11 or later.
- Node.js 20 or later.
- Git.
- Android phone.
- Expo Go for compatible development workflows.

### Step 1 — Clone the Repository

```powershell
git clone https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system.git

cd Tourist-Safety-monitoring-system
```

### Step 2 — Configure Backend

```powershell
cd backend

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
```

Start FastAPI:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend:

`http://localhost:8000`

API Documentation:

`http://localhost:8000/docs`

### Step 3 — Start Dashboard

Open another terminal:

```powershell
cd dashboard

copy .env.example .env.local

npm install

npm run dev
```

Dashboard:

`http://localhost:3000`

### Step 4 — Start Mobile Application

Open another terminal:

```powershell
cd mobile

copy .env.example .env

npm install

npx expo install --fix

npx expo start
```

For physical Android device testing:

1. Run `ipconfig` on Windows.
2. Find your computer's Wi-Fi IPv4 address.
3. Configure `EXPO_PUBLIC_API_URL` in `mobile/.env`.
4. Use your computer's IP address instead of localhost.
5. Connect your phone and computer to the same Wi-Fi network.
6. Scan the Expo QR code.

Example:

```env
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000
```

Replace the example IP with your actual local network address.

---

## 🌐 11. Local Development URLs

| Service | URL |
|---|---|
| Backend | http://localhost:8000 |
| Backend Health | http://localhost:8000/health |
| Database Readiness | http://localhost:8000/ready |
| API Documentation | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |

---

## 🚀 12. Deployment Guide

SafeTrail is prepared for a Render + Vercel + Expo EAS deployment workflow.

### A. Backend Deployment — Render

1. Open [Render](https://render.com/).
2. Sign in using GitHub.
3. Select New → Blueprint.
4. Connect the SafeTrail repository.
5. Allow Render to read `render.yaml`.
6. Configure production environment variables.
7. Provision and verify the production database.
8. Deploy the FastAPI backend.
9. Verify the health endpoint.

Example:

```text
https://your-api.onrender.com/health
```

### B. Dashboard Deployment — Vercel

1. Open [Vercel](https://vercel.com/).
2. Import the GitHub repository.
3. Select `dashboard` as the root directory.
4. Configure environment variables.
5. Set the production API URL.
6. Deploy the dashboard.
7. Configure backend CORS with the deployed dashboard domain.

Example:

```env
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

### C. Android APK — Expo EAS

Install the EAS CLI:

```powershell
npm install -g eas-cli
```

Authenticate:

```powershell
eas login
```

Configure:

```powershell
cd mobile

eas init
```

Build the Android preview APK:

```powershell
eas build -p android --profile preview
```

Ensure production API configuration and Android permissions are correct before building.

### D. Email Configuration

Configure Brevo or another supported provider.

Example:

```env
EMAIL_API_KEY=your_provider_api_key
EMAIL_FROM=verified_sender@example.com
```

Do not commit actual credentials.

### Deployment Notes

- Render free services may have cold starts and resource limitations.
- Verify PostgreSQL availability and persistence for the selected plan.
- Render's free web services do not support normal outbound SMTP; use a compatible email API.
- Verify production notification delivery.
- Keep all production secrets in provider environment settings.

---

## 🧪 13. Testing and Quality Assurance

SafeTrail includes automated testing across the major components.

### Backend

```powershell
cd backend

pip install -r requirements-dev.txt

pytest -q
```

### Dashboard

```powershell
cd dashboard

npm run lint

npm run typecheck

npm test

npm run build
```

### Mobile

```powershell
cd mobile

npm run typecheck

npm test
```

### Previously Reported Test Results

| Component | Reported result |
|---|---|
| Backend | 82 passed, 1 skipped |
| Dashboard | Tests, lint and typecheck passed |
| Mobile | 8 tests passed |
| Performance smoke test | Approximately 8–9 ms per in-process location update |

These are previously reported results, not a guarantee that every subsequent build or external integration will pass.

### Critical End-to-End Test

Verify the following workflow:

```text
Tourist Login
      ↓
GPS Permission
      ↓
Live Location
      ↓
Restricted Zone Detection
      ↓
Safety Notification
      ↓
Tourist SOS
      ↓
Admin Alert
      ↓
Police Acknowledgement
      ↓
Incident Resolution
```

---

## ⚠️ 14. Current Limitations and Deployment Considerations

The following points must be considered before declaring the system production-ready:

1. The original SQLite database is private and is not included in GitHub.
2. The historical database audit reported six tourists, 209 safety zones and five SOS records.
3. The 209 reported zones consist of 200 synthetic `DEMO-KA` zones and nine SVIT demonstration zones.
4. The nine SVIT zones were previously reported with a 200-metre radius; the requested 50-metre change remains unverified.
5. Original geographical KML dataset provenance is not yet independently verified.
6. Background location and push functionality require appropriate native Android builds and permissions.
7. The AI intelligence engine uses explainable rule-based logic; it is not a validated predictive ML model.
8. SMS integration is not implemented.
9. Real email delivery requires provider configuration.
10. Production database migration and real-device testing must be completed before final production acceptance.

---

## 📚 15. Project Documentation

Additional technical documentation is available in the `docs/` directory.

| Document | Purpose |
|---|---|
| PROJECT_OVERVIEW.md | Project introduction |
| SYSTEM_ARCHITECTURE.md | System architecture |
| DATABASE_DESIGN.md | Database structure |
| API_DOCUMENTATION.md | Backend endpoints |
| AUTHENTICATION.md | Authentication design |
| GPS_AND_LOCATION.md | Location functionality |
| GEOFENCING.md | Geofence implementation |
| DATASET_DOCUMENTATION.md | Dataset inventory |
| SOS_WORKFLOW.md | Emergency workflow |
| AI_INTELLIGENCE.md | AI implementation |
| SECURITY_AUDIT.md | Security review |
| TESTING_REPORT.md | Test results |
| DEPLOYMENT_GUIDE.md | Deployment process |
| ENVIRONMENT_VARIABLES.md | Configuration |
| FINAL_COMPLETION_REPORT.md | Implementation status |

---

## 🎓 16. Project Significance

SafeTrail demonstrates the integration of modern software engineering technologies to address a real-world safety challenge.

### Key Technical Contributions

- Full-stack application development.
- Mobile GPS integration.
- Geospatial data processing.
- Real-time monitoring.
- Secure role-based authentication.
- Emergency incident management.
- Explainable safety intelligence.
- Interactive GIS dashboards.
- Automated software testing.
- Cloud deployment architecture.

### Expected Impact

- Improve tourist safety awareness.
- Support faster emergency communication.
- Help authorities monitor geographical risks.
- Improve coordination between tourists and emergency responders.
- Provide a centralized platform for safety management.

---

## 👨‍💻 17. Project Information

| Field | Details |
|---|---|
| Project Name | SafeTrail |
| Full Name | Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform |
| Project Category | Full-Stack Software Engineering |
| Application Type | Web + Android |
| Architecture | Software-only |
| Backend | FastAPI |
| Dashboard | Next.js |
| Mobile | Expo React Native |
| Database | SQLite / PostgreSQL |
| Repository | [GitHub Repository](https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system) |
| Academic Year | 2026 |

---

<div align="center">

## 🛡️ SafeTrail

### Travel Freely. Stay Aware. Stay Safe.

**Building a smarter digital safety ecosystem for tourists.**

<br/>

⭐ If you find this project interesting, consider starring the repository.

[GitHub Repository](https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system)

<br/>

*Developed as a major software engineering project · 2026*

</div>
