# Deployment guide (free tier)

The short version is in the [README](../README.md#-deploy-for-free--render--vercel). Details:

## Backend — Render
* Blueprint: `render.yaml` → web service `safetrail-api` (Python 3.12, `rootDir: backend`, health check `/health`) + PostgreSQL `safetrail-db` (free).
* Migrations run automatically on start (additive). `/ready` checks the DB.
* Free web services sleep when idle; the first request after sleeping is slow. Uptime monitors that ping `/health` keep it warm but count against free hours.
* Free PostgreSQL databases expire after a limited period — back up regularly:
  ```bash
  pg_dump "<External Database URL>" > safetrail_$(date +%F).sql
  psql "<new database URL>" < safetrail_YYYY-MM-DD.sql
  ```
* Render free instances block outbound SMTP; use `EMAIL_PROVIDER=brevo` (HTTPS API).

## Dashboard — Vercel
Root directory `dashboard`, env `NEXT_PUBLIC_API_URL`. Then add the Vercel URL to `ALLOWED_ORIGINS` on Render.

## Mobile — EAS
`eas init` (adds the projectId needed for push) → set `EXPO_PUBLIC_API_URL` in `eas.json` → `eas build -p android --profile preview` (APK). Do not publish to Play Store without review of the privacy policy and background-location declaration.

## Moving the existing SQLite data
```bash
cd backend
python -m app.migrations --status
python -m app.scripts.copy_sqlite_to_postgres --source sqlite:///./tourist_safety.db --target "<External Database URL>"
```

## Docker (any host)
`docker compose up --build` runs PostgreSQL, API (8000) and dashboard (3000) locally.

## Post-deploy checks
1. `GET /health` → healthy; `GET /ready` → database ok.
2. Sign in with the bootstrap admin; **Settings → System status** shows `postgresql`, schema v2, email/push status.
3. **Dataset management** counts match the audit of the local database.
4. Create a police account, register/link a tourist Gmail, sign in on the phone, share location, enter a test zone, raise an SOS, acknowledge → accept → resolve.

## Actions that need you (credentials / approval)
Render account + Blueprint apply · Vercel account + project · Brevo account, API key and verified sender · Expo account + `eas init` + build · data copy from your local `tourist_safety.db`. Nothing was deployed by this work.
