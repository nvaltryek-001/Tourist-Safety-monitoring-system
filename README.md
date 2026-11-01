<div align="center">

# 🛡️ SafeTrail

### Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform

Live GPS safety monitoring with consent · geofenced restricted zones · one-tap SOS · police & admin command console · explainable safety intelligence

![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Dashboard-Next.js%2015-000000?logo=nextdotjs)
![Expo](https://img.shields.io/badge/Mobile-Expo%20%2F%20React%20Native-000020?logo=expo)
![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL%20%7C%20SQLite-336791?logo=postgresql&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render%20%2B%20Vercel%20(free)-46E3B7)
![Software only](https://img.shields.io/badge/Hardware-none%20(phone%20GPS%20only)-lightgrey)

</div>

---

## 📌 Contents

1. [What it does](#-what-it-does)
2. [Architecture](#-architecture)
3. [Login & passwords](#-login--passwords) ← **start here**
4. [Run it locally (5 minutes)](#-run-it-locally)
5. [Deploy for free — Render + Vercel](#-deploy-for-free--render--vercel)
6. [Tourist mobile app](#-tourist-mobile-app)
7. [Moving your existing data](#-moving-your-existing-database-to-the-cloud)
8. [Testing](#-testing)
9. [Project structure](#-project-structure)
10. [Documentation](#-documentation)

---

## ✨ What it does

| For tourists (Android app) | For admins (web) | For police officers (web) |
|---|---|---|
| Passwordless **Gmail OTP** sign-in | Live KPIs from the real database | Own workspace: assigned + nearby SOS |
| Clear **consent** before any location is shared | **Live map** over WebSocket, clustering, stale markers | Accept → respond → resolve with notes |
| Real phone **GPS**, offline queue, auto-retry | **SOS command centre** (New → Acknowledged → Responding → Resolved) | Navigate to the tourist in Google Maps |
| Safety status: Safe · Caution · Restricted · Emergency · Location unavailable | Zone editor + **GeoJSON / KML import & export** | Contact details visible **only** during an active SOS |
| **Hold-to-confirm SOS**, idempotent, server-confirmed | Tourist login allow-list, officer accounts, audit log | Incident timeline & response history |
| Emergency status tracking, alerts, trips, history | **AI safety intelligence** (explainable risk scores) | Analytics & AI advisories |

> **Honesty rules built in:** an SOS is only shown as sent after the server confirms it · notifications report `ACCEPTED_BY_PROVIDER`, never "delivered" · the app never says "Safe" without a live location · AI output is labelled **advisory**, never a confirmed emergency · synthetic test zones are flagged purple everywhere.

---

## 🏗 Architecture

```
 ┌──────────────────┐      HTTPS / JSON       ┌──────────────────────────┐      ┌──────────────┐
 │ Tourist app      │ ──────────────────────▶ │  FastAPI backend (Render)│ ───▶ │ PostgreSQL   │
 │ Expo · Android   │ ◀── push (Expo) ─────── │  auth · geofence · SOS   │      │ (Render free)│
 └──────────────────┘                         │  AI advisories · audit   │      │  or SQLite   │
 ┌──────────────────┐   REST + WebSocket /ws  │  notifications           │      └──────────────┘
 │ Admin & Police   │ ◀─────────────────────▶ │                          │ ───▶ Brevo / Resend email
 │ Next.js (Vercel) │                         └──────────────────────────┘
 └──────────────────┘
```

All three apps use **one** backend and **one** database. The mobile app never touches the database directly.

---

## 🔐 Login & passwords

### 1. Local demo staff accounts (your computer only)

When you run the backend locally with `SEED_DEMO_STAFF=true` (the default in `backend/.env.example`), these accounts are created automatically:

| Role | Email | Password | Lands on |
|---|---|---|---|
| 👑 Super Admin | `superadmin@demo.local` | `SuperAdmin@123` | Overview — can create admins |
| 🛠 Admin | `admin@demo.local` | `Admin@12345` | Overview — tourists, zones, officers |
| 🚓 Police Officer | `police@demo.local` | `Police@12345` | Officer workspace |

> ⚠️ These demo accounts are **disabled automatically when `ENVIRONMENT=production`** (which `render.yaml` sets), because this repository is public and anyone can read this table. Change them under **Settings → Change password** if you keep them for a local demo.

### 2. Your real admin account (production on Render)

You choose it yourself — it is never stored in the repo:

| Render environment variable | Example |
|---|---|
| `BOOTSTRAP_ADMIN_EMAIL` | `you@yourcollege.edu` |
| `BOOTSTRAP_ADMIN_PASSWORD` | 10+ characters with UPPER, lower and a digit, e.g. `Kept-Secret-2026` |

On first start the backend creates that **Super Admin** (it never overwrites an existing account). Sign in on the dashboard, then create police officers under **Officers & staff**.

### 3. Tourist login (mobile app) — Gmail, no password

1. An admin registers the tourist (**Tourists → Register tourist**) or links an existing one under **Tourist login access** to their **Gmail** address.
2. The tourist types that Gmail in the app → receives a **6-digit code** (valid 5 minutes, single use, 5 attempts max).
3. Only Gmail addresses on the allow-list can sign in — the six existing tourists keep their existing records; no accounts are invented.

| How the code arrives | Setting |
|---|---|
| ✅ Real email (free) | `EMAIL_PROVIDER=brevo`, `EMAIL_API_KEY=<Brevo key>`, `EMAIL_FROM=<sender verified in Brevo>` |
| 🧪 Demo without email | `OTP_DEV_ECHO=true` — the app shows the code in a yellow **"Demo mode – NOT emailed"** box |

### Security at a glance
PBKDF2-SHA256 password hashing · account lock for 15 min after 5 failed logins · JWT sessions stored server-side (logout and "sign out other devices" really revoke them) · rate-limited OTP and SOS · every login, data view and incident action is in the **Audit log**.

---

## 💻 Run it locally

**Requirements:** Python 3.11+, Node 20+, (optional) Docker.

```bash
# 1) Backend  → http://localhost:8000  (API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Your existing `tourist_safety.db` is used as-is. On first start the schema is upgraded **additively** and a backup is written to `backend/backups/` first — no rows are deleted or changed.

```bash
# 2) Dashboard → http://localhost:3000
cd dashboard
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

```bash
# 3) Mobile app (Expo Go on your Android phone, same Wi-Fi)
cd mobile
cp .env.example .env              # EXPO_PUBLIC_API_URL=http://<your-PC-LAN-IP>:8000
npm install && npx expo install --fix
npx expo start                    # scan the QR code with Expo Go
```

Or everything at once with PostgreSQL: `docker compose up --build`.

---

## 🚀 Deploy for free — Render + Vercel

Everything below uses **free plans**, no credit card needed for Vercel; Render's free plan is used for both the API and PostgreSQL.

### Step 1 — Backend + database on Render

1. Sign in at **render.com** with GitHub → **New ➜ Blueprint** → choose this repository.
2. Render reads [`render.yaml`](render.yaml) and creates `safetrail-api` (free web service) and `safetrail-db` (free PostgreSQL).
3. Fill in the prompted values:
   - `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` → your super-admin login
   - `ALLOWED_ORIGINS` → leave `http://localhost:3000` for now (updated in step 3)
   - `EMAIL_API_KEY`, `EMAIL_FROM` → from a free **brevo.com** account (Settings → SMTP & API → API key; verify your Gmail as a sender). Leave empty to skip email.
4. Click **Apply**. When it is live, open `https://<your-api>.onrender.com/health` → `{"status":"healthy"}`.

> `SECRET_KEY` is generated by Render automatically. Free instances sleep after 15 minutes idle (first request takes ~1 min), and Render free PostgreSQL databases expire after a limited time — export a backup before then (see [Deployment guide](docs/DEPLOYMENT_GUIDE.md)).

### Step 2 — Dashboard on Vercel

1. Sign in at **vercel.com** with GitHub → **Add New ➜ Project** → import this repository.
2. **Root Directory:** `dashboard` (framework auto-detected as Next.js).
3. **Environment Variable:** `NEXT_PUBLIC_API_URL` = `https://<your-api>.onrender.com`
4. **Deploy** → you get `https://<your-project>.vercel.app`.

### Step 3 — Connect them

On Render → `safetrail-api` → **Environment** → set `ALLOWED_ORIGINS=https://<your-project>.vercel.app` → **Save** (it redeploys). Sign in to the dashboard with your bootstrap admin.

### Step 4 — Android APK (free Expo account)

```bash
cd mobile
npm install -g eas-cli && eas login
eas init                                   # links a free Expo project (adds projectId)
# put your Render URL in eas.json → build.preview.env.EXPO_PUBLIC_API_URL
eas build -p android --profile preview     # downloadable .apk, push notifications work
```

---

## 📱 Tourist mobile app

20 screens: splash · welcome · Gmail login · OTP verification · privacy & location consent · home status · safety-zone map with search/filter/legend · nearby safety information · active trip · SOS (hold 1.5 s → confirm) · emergency status tracking · emergency contacts & Indian helplines (112/100/108/1363) · notification centre · travel history · AI safety report · settings · profile & sign-out.

- **GPS:** real `expo-location` fixes (balanced accuracy, every 25 m / 30 s), accuracy shown, permission revocation detected when the app returns to the foreground.
- **Offline:** every fix is queued with a unique id and uploaded in batches with exponential backoff; the server ignores replays.
- **Background:** optional during trips in the APK build (foreground-service notification). Not available inside Expo Go.
- **Push:** works in the EAS APK; Expo Go shows in-app alerts instead and says so.

---

## 🗄 Moving your existing database to the cloud

The real database (`backend/tourist_safety.db`: 6 tourists, 209 zones, 5 SOS records at the last audit) is intentionally **not** in Git. To copy it to Render PostgreSQL without retyping anything:

```bash
cd backend
python -m app.scripts.audit_db --json db_audit_before.json          # read-only, no personal data
python -m app.scripts.copy_sqlite_to_postgres \
  --source sqlite:///./tourist_safety.db \
  --target "<Render External Database URL>"
```

The copy refuses to write into non-empty tables, keeps every ID (so `College Demo Zone` IDs match), and prints source vs target row counts.

---

## 🧪 Testing

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q
cd dashboard && npm run lint && npm run typecheck && npm test && npm run build
cd mobile && npm run typecheck && npm test
```

GitHub Actions runs all three on every push (`.github/workflows/ci.yml`). Current results are recorded in [docs/TESTING_REPORT.md](docs/TESTING_REPORT.md).

---

## 📂 Project structure

```
backend/      FastAPI API · services (geofence, SOS, AI, notifications) · additive migrations · tests
dashboard/    Next.js 15 admin + police console (Tailwind, Leaflet/OSM, Recharts)
mobile/       Expo Router tourist app (expo-location, react-native-maps, SecureStore)
docs/         Architecture, API, security, datasets, deployment, final report
render.yaml   Render blueprint (free API + free PostgreSQL)
docker-compose.yml   Local full stack
```

## 📚 Documentation

[Overview](docs/PROJECT_OVERVIEW.md) · [Architecture](docs/SYSTEM_ARCHITECTURE.md) · [Database](docs/DATABASE_DESIGN.md) · [API](docs/API_DOCUMENTATION.md) · [Authentication](docs/AUTHENTICATION.md) · [GPS](docs/GPS_AND_LOCATION.md) · [Geofencing](docs/GEOFENCING.md) · [Datasets](docs/DATASET_DOCUMENTATION.md) · [SOS workflow](docs/SOS_WORKFLOW.md) · [AI](docs/AI_INTELLIGENCE.md) · [Security](docs/SECURITY_AUDIT.md) · [Testing](docs/TESTING_REPORT.md) · [Deployment](docs/DEPLOYMENT_GUIDE.md) · [Environment variables](docs/ENVIRONMENT_VARIABLES.md) · [Known limitations](docs/KNOWN_LIMITATIONS.md) · [Final report](docs/FINAL_COMPLETION_REPORT.md)

---

<div align="center">
Software-only · no IoT hardware · built as a major academic project with production-grade safeguards.
</div>
