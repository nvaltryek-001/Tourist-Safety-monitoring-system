<div align="center">

# 🛡️ SafeTrail
### Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform

Real-time tourist safety using phone GPS, geofenced danger zones, one-tap SOS, and a live command dashboard for admins and police.

![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Dashboard-Next.js-000000?logo=nextdotjs)
![Expo](https://img.shields.io/badge/Mobile-Expo%20React%20Native-000020?logo=expo)
![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791?logo=postgresql&logoColor=white)
![Hardware](https://img.shields.io/badge/Hardware-None%20(software%20only)-lightgrey)

</div>

---

## 📖 About the Project

SafeTrail is a **software-only** safety platform for tourists. Tourists share their live phone location (only after giving consent), get warned when they enter restricted or high-risk zones, and can send an **SOS** with one press. Administrators and police officers watch everything live on a web dashboard and respond to emergencies.

There is **no IoT or hardware**. Location comes from the smartphone's own GPS, and SOS is a button in the app.

---

## ✨ Features

### 📱 Tourist Mobile App (Android)
- Passwordless login with **Gmail + 6-digit OTP**
- Clear **privacy & location consent** screen before any sharing
- Real **phone GPS** tracking with accuracy display
- **Offline queue**: locations are saved without internet and uploaded later
- Live safety status: **Safe · Caution · Restricted Zone · Emergency · Location Unavailable**
- **Safety map** with zones, search, filters and legend
- **Hold-to-confirm SOS**, shown as sent only after the server confirms it
- Emergency status tracking (Received → Acknowledged → Responding → Resolved)
- Alerts, trips, travel history, AI safety report, emergency contacts (112 / 100 / 108 / 1363)

### 🖥️ Admin Dashboard (Web)
- Live KPIs from the real database
- **Live map** with real-time updates (WebSocket) and marker clustering
- **SOS Command Centre**: acknowledge, assign officer, resolve with notes
- Tourist management with search, filters and location history
- **Safety zone editor**: add, edit, deactivate, import/export **GeoJSON & KML**
- Dataset audit (zone counts, duplicates, overlaps)
- Tourist Gmail login access list, officer accounts, audit log
- AI safety intelligence and analytics charts

### 🚓 Police Dashboard (Web)
- Officer workspace: assigned incidents plus nearby unassigned SOS alerts
- Accept → Respond → Resolve, with an incident timeline and notes
- Navigate to the tourist through Google Maps
- Tourist contact details visible **only while handling an active SOS**

### 🧠 AI Safety Intelligence
- Prolonged stationary detection
- Unusual route deviation (statistical anomaly check)
- High-risk and repeated restricted-zone entry
- Tourist risk score (0–100) with reasons and evidence
- Zone risk ranking, incident trends, hazard report
- Every result is labelled **"AI Advisory"**, never treated as a confirmed emergency

---

## 🛠️ What We Built (Upgrade Summary)

| Before | After |
|---|---|
| Basic FastAPI with 8 public endpoints | Full API (~75 endpoints) with authentication and roles |
| No login system | Gmail OTP for tourists, passwords for staff, 4 roles |
| Tourist data publicly visible | Protected, role-based access, privacy masking for police |
| Simple SOS record | Full SOS lifecycle with timeline, assignment and duplicate protection |
| No mobile app | Expo Android app with 20 screens |
| No dashboard | Next.js admin + police dashboard with 15 pages |
| No real-time updates | WebSocket live map and alerts |
| No AI | Explainable safety intelligence engine |
| No tests in CI | Automated tests on GitHub Actions (82 backend tests passing) |
| No deployment setup | Ready for free hosting on Render + Vercel |

> The existing database is **never deleted**. Upgrades only **add** new tables and columns, and an automatic backup is made first.

---

## 🧰 Tech Stack

| Part | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, PyJWT |
| Database | SQLite (local), PostgreSQL (cloud) |
| Dashboard | Next.js 15, React, TypeScript, Tailwind CSS, Leaflet (OpenStreetMap), Recharts |
| Mobile | Expo, React Native, TypeScript, Expo Router, Expo Location, React Native Maps |
| Real-time | WebSocket |
| Email | Brevo / Resend / SMTP (optional) |
| Push | Expo Push Notifications |
| Testing | Pytest, Vitest, TypeScript strict mode, GitHub Actions |
| Hosting | Render (API + DB), Vercel (dashboard), Expo EAS (APK) |

---

## 🏗️ Architecture

```
 ┌──────────────────┐        HTTPS          ┌─────────────────────────┐      ┌─────────────┐
 │ Tourist App      │ ────────────────────▶ │  FastAPI Backend        │ ───▶ │  Database   │
 │ (Expo / Android) │ ◀──── Push alerts ─── │  Auth · Geofence · SOS  │      │ SQLite /    │
 └──────────────────┘                       │  AI · Notifications     │      │ PostgreSQL  │
 ┌──────────────────┐   REST + WebSocket    │                         │      └─────────────┘
 │ Admin & Police   │ ◀───────────────────▶ │                         │
 │ Dashboard        │                       └─────────────────────────┘
 └──────────────────┘
```

All three parts use **one backend and one database**.

---

## 🔐 Login Details

### Staff accounts (local demo only)

| Role | Email | Password |
|---|---|---|
| 👑 Super Admin | `superadmin@demo.local` | `SuperAdmin@123` |
| 🛠️ Admin | `admin@demo.local` | `Admin@12345` |
| 🚓 Police Officer | `police@demo.local` | `Police@12345` |

> These demo accounts work **only on a local computer**. They are switched off automatically in production.
> For the live server, set your own admin with `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`.

### Tourist login (mobile app)
1. An admin links the tourist to their **Gmail** under **Tourist Login Access**.
2. The tourist enters that Gmail in the app.
3. A **6-digit code** is sent (valid 5 minutes, one use only).
4. Without email set up, demo mode shows the code in a yellow box in the app.

Only approved Gmail addresses can log in.

---

## 💻 Run Locally on Windows

### Requirements
- **Python 3.11+**: tick "Add python.exe to PATH" during install
- **Node.js 20+** (LTS)
- **Git**
- **Expo Go** app on an Android phone (from the Play Store)

### 1️⃣ Download the project
```powershell
cd C:\Users\<your-name>
git clone https://github.com/nvaltryek-001/Tourist-Safety-monitoring-system.git
cd Tourist-Safety-monitoring-system
```

> 💾 If you have the existing database file `tourist_safety.db`, copy it into the `backend` folder **before** starting the backend.

### 2️⃣ Start the backend (Terminal 1, keep open)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
If PowerShell blocks `activate`, run this once and try again:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3️⃣ Start the dashboard (Terminal 2, keep open)
```powershell
cd dashboard
copy .env.example .env.local
npm install
npm run dev
```

### 4️⃣ Start the Android app (Terminal 3)
```powershell
ipconfig
cd mobile
copy .env.example .env
npm install
npx expo install --fix
npx expo start
```
1. From `ipconfig`, note your **Wi-Fi IPv4 address** (for example `192.168.1.10`).
2. Edit `mobile\.env` and set `EXPO_PUBLIC_API_URL=http://192.168.1.10:8000`, using your own IP.
3. Connect the phone to the **same Wi-Fi** as the computer.
4. Open **Expo Go** and scan the QR code.
5. If Windows asks about network access for Python or Node, click **Allow**.

### 🌐 Local URLs

| What | URL |
|---|---|
| Backend health | http://localhost:8000/health |
| Database check | http://localhost:8000/ready |
| API documentation | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |
| Phone test | http://YOUR-PC-IP:8000/health (open in the phone browser) |

---

## 🚀 Free Deployment

### Backend + database: Render
1. Sign in to **render.com** with GitHub → **New → Blueprint** → select this repo.
2. Render reads `render.yaml` and creates the API and a free PostgreSQL database.
3. Fill in `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`.
4. Optional real email: a free **Brevo** API key in `EMAIL_API_KEY` and a verified sender in `EMAIL_FROM`.
5. Check `https://your-api.onrender.com/health`.

### Dashboard: Vercel
1. Sign in to **vercel.com** with GitHub → **Add New Project** → this repo.
2. Root Directory: `dashboard`
3. Environment variable: `NEXT_PUBLIC_API_URL = https://your-api.onrender.com`
4. Deploy.
5. On Render, set `ALLOWED_ORIGINS = https://your-project.vercel.app`.

### Android APK: Expo EAS
```powershell
cd mobile
npm install -g eas-cli
eas login
eas init
eas build -p android --profile preview
```
Before building, set your Render URL in `eas.json`.

> ℹ️ Render's free tier blocks normal SMTP email, so this project uses **Brevo** (a free email API) instead.

---

## 🧪 Testing

```powershell
# Backend
cd backend
pip install -r requirements-dev.txt
pytest -q

# Dashboard
cd dashboard
npm run lint
npm run typecheck
npm test
npm run build

# Mobile
cd mobile
npm run typecheck
npm test
```

### Results (GitHub Actions)

| Suite | Result |
|---|---|
| Backend tests | ✅ 82 passed, 1 skipped (needs a live server) |
| Dashboard lint, types, tests, build | ✅ Passed |
| Mobile types and tests | ✅ Passed |
| Performance smoke test | ✅ ~8–9 ms per location update (in-process) |

---

## 🔒 Security & Privacy

- Location shared **only after consent**, and the tourist can delete their history
- Passwords hashed with PBKDF2-SHA256
- Account locks for 15 minutes after 5 wrong passwords
- Logout and "sign out other devices" end sessions immediately
- Rate limits on OTP, login, location updates and SOS
- Police see contact details only during an active SOS
- Every login, data view and incident action is recorded in the **Audit Log**
- Location history is removed after 30 days by default
- No passwords, API keys or personal data are stored in the code

---

## 📂 Project Structure

```
Tourist-Safety-monitoring-system/
├── backend/          FastAPI API, services, migrations, tests
├── dashboard/        Next.js admin + police dashboard
├── mobile/           Expo Android tourist app
├── docs/             Full documentation and reports
├── render.yaml       Render free deployment setup
├── docker-compose.yml
└── README.md
```

---

## 📚 Documentation

| Topic | File |
|---|---|
| Project overview | `docs/PROJECT_OVERVIEW.md` |
| Architecture | `docs/SYSTEM_ARCHITECTURE.md` |
| Database | `docs/DATABASE_DESIGN.md` |
| API | `docs/API_DOCUMENTATION.md` |
| Authentication | `docs/AUTHENTICATION.md` |
| GPS & location | `docs/GPS_AND_LOCATION.md` |
| Geofencing | `docs/GEOFENCING.md` |
| Datasets | `docs/DATASET_DOCUMENTATION.md` |
| SOS workflow | `docs/SOS_WORKFLOW.md` |
| AI intelligence | `docs/AI_INTELLIGENCE.md` |
| Security audit | `docs/SECURITY_AUDIT.md` |
| Testing report | `docs/TESTING_REPORT.md` |
| Deployment guide | `docs/DEPLOYMENT_GUIDE.md` |
| Environment variables | `docs/ENVIRONMENT_VARIABLES.md` |
| Known limitations | `docs/KNOWN_LIMITATIONS.md` |
| Final report | `docs/FINAL_COMPLETION_REPORT.md` |

---

## ⚠️ Known Limitations

- The real database (`tourist_safety.db`) is kept private and is not on GitHub.
- The 209 safety zones = 200 synthetic test zones (`DEMO-KA`) + 9 college demo zones.
- The college demo zones are stored at 200 m (a 50 m change was requested but not yet applied).
- Background location and push notifications need the APK build; they don't work in Expo Go.
- The AI is rule-based. There is not enough real incident data to train an ML model.
- SMS alerts are not implemented.

---

## 👥 Team

| Name | Role |
|---|---|
| _Your Name_ | _Role_ |
| _Team Member_ | _Role_ |

**Guide:** _Guide Name_ · **College:** _College Name_ · **Year:** 2026

---

<div align="center">

Made with ❤️ as a Major Project · Software-only · Privacy-first

</div>
