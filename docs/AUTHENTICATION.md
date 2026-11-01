# Authentication

## Tourists — passwordless Gmail OTP
1. `request-otp` accepts only `@gmail.com` / `@googlemail.com` and only addresses present and active in `tourist_access` whose tourist exists (otherwise 403). Gmail dot/`+tag` variants are normalised to one identity.
2. A 6-digit code is generated with `secrets`, stored as `HMAC-SHA256(SECRET_KEY, email:code)`, expires after `OTP_TTL_SECONDS` (300), earlier unused codes are invalidated.
3. Delivery: the configured provider (`brevo`, `resend`, `smtp`). The response states `delivery: ACCEPTED_BY_PROVIDER | NOT_CONFIGURED | FAILED`. With `OTP_DEV_ECHO=true` and no provider the code is returned as `dev_otp` with an explicit "NOT emailed" message.
4. `verify-otp` allows `OTP_MAX_ATTEMPTS` (5) wrong codes, marks the code used (one-time) and issues a JWT valid `TOURIST_TOKEN_DAYS` (7).
5. Rate limits: 3 code requests per email per 10 min, 10 per IP; 20 verify attempts per IP.

## Staff — email + password
PBKDF2-SHA256 (260 000 iterations, per-user salt). Password policy: 10+ chars, upper, lower, digit. 5 failed logins lock the account for 15 min (HTTP 423). Tokens expire after `ACCESS_TOKEN_MINUTES` (720). Changing a password revokes the user's other sessions. Only a super admin can create/modify admin accounts; admins create police accounts.

## Sessions
Every JWT carries a `jti` that must exist, be unexpired and not revoked in `auth_sessions`, so logout, per-device revocation and "sign out other devices" take effect immediately for REST and WebSocket.

## Bootstrapping
`BOOTSTRAP_ADMIN_EMAIL/PASSWORD` create a super admin once. `SEED_DEMO_STAFF=true` creates the README's demo accounts, but never when `ENVIRONMENT=production`.

## Audit
`STAFF_LOGIN`, `STAFF_LOGIN_FAILED`, `TOURIST_LOGIN`, `TOURIST_LOGIN_FAILED`, `TOURIST_OTP_REQUESTED/REJECTED`, `LOGOUT`, `SESSION_REVOKED`, `STAFF_PASSWORD_CHANGED` and more are written to `audit_logs` (no codes, passwords or raw locations).
