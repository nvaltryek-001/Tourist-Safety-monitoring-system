# Environment variables

Configuration names only — never commit real values.

## Backend (`backend/.env`, Render)
| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./tourist_safety.db` | SQLAlchemy URL; `postgres://` and `postgresql://` are normalised to psycopg 3 |
| `ENVIRONMENT` | `development` | `production` enforces a strong `SECRET_KEY` and disables demo staff |
| `SECRET_KEY` | dev placeholder | JWT + OTP HMAC key (32+ chars in production; Render generates it) |
| `ALLOWED_ORIGINS` | localhost:3000, :8081 | comma-separated dashboard origins |
| `ALLOWED_ORIGIN_REGEX` | — | optional, e.g. preview deployments |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | — | create the first super admin once |
| `SEED_DEMO_STAFF` | `false` | create README demo accounts (non-production only) |
| `EMAIL_PROVIDER` | `none` | `brevo`, `resend`, `smtp` or `none` |
| `EMAIL_API_KEY` | — | Brevo/Resend API key, or SMTP password (also reads `RESEND_API_KEY`) |
| `EMAIL_FROM` | — | verified sender (also reads `RESEND_FROM_EMAIL`) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` | smtp.gmail.com / 587 / — | for `EMAIL_PROVIDER=smtp` |
| `ADMIN_ALERT_EMAIL` | — | receives SOS alert emails |
| `OTP_DEV_ECHO` | `false` | demo only: return OTP in the API response |
| `EXPO_PUSH_ENABLED` | `false` | send Expo push notifications |
| `PUSH_NOTIFICATION_CREDENTIALS` | — | optional Expo access token |
| `GOOGLE_MAPS_API_KEY` | — | reserved; maps use OpenStreetMap (web) and the platform map (mobile) |
| `ACCESS_TOKEN_MINUTES` | 720 | staff session length |
| `TOURIST_TOKEN_DAYS` | 7 | tourist session length |
| `OTP_TTL_SECONDS` / `OTP_MAX_ATTEMPTS` | 300 / 5 | OTP lifetime and attempts |
| `OTP_REQUESTS_PER_WINDOW` / `OTP_WINDOW_SECONDS` | 3 / 600 | OTP request limit per email |
| `STAFF_MAX_FAILED_LOGINS` / `STAFF_LOCKOUT_MINUTES` | 5 / 15 | lockout |
| `LOCATION_RETENTION_DAYS` | 30 | purge threshold |
| `STALE_LOCATION_MINUTES` | 15 | marks positions stale |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 10 | PostgreSQL pool |
| `SKIP_MIGRATIONS` | `false` | skip the automatic additive upgrade on start |
| `LOG_LEVEL` | `INFO` | logging |

## Dashboard (Vercel)
| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | backend base URL (public by design — no secrets here) |

## Mobile (Expo / EAS)
| Variable | Purpose |
|---|---|
| `EXPO_PUBLIC_API_URL` | backend base URL baked into the build |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | only needed if you switch Android maps to a custom Google key in a standalone build |
