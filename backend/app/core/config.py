"""Central runtime configuration, read from environment variables.

Nothing secret has a usable default in production: when ENVIRONMENT=production
the app refuses to start with the development SECRET_KEY.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

try:  # optional: load backend/.env for local development
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


DEV_SECRET = "dev-only-insecure-secret-change-me"


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", DEV_SECRET))
    allowed_origins: list[str] = field(
        default_factory=lambda: _list(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081",
        )
    )
    # Regex for preview deployments, e.g. https://.*\.vercel\.app
    allowed_origin_regex: str | None = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGIN_REGEX") or None
    )

    access_token_minutes: int = field(default_factory=lambda: _int("ACCESS_TOKEN_MINUTES", 60 * 12))
    tourist_token_days: int = field(default_factory=lambda: _int("TOURIST_TOKEN_DAYS", 7))

    otp_ttl_seconds: int = field(default_factory=lambda: _int("OTP_TTL_SECONDS", 300))
    otp_max_attempts: int = field(default_factory=lambda: _int("OTP_MAX_ATTEMPTS", 5))
    otp_requests_per_window: int = field(default_factory=lambda: _int("OTP_REQUESTS_PER_WINDOW", 3))
    otp_window_seconds: int = field(default_factory=lambda: _int("OTP_WINDOW_SECONDS", 600))
    # Development / demo only: return the OTP in the API response because no
    # email provider is configured. The response says so explicitly.
    otp_dev_echo: bool = field(default_factory=lambda: _bool("OTP_DEV_ECHO", False))
    tourist_email_domains: list[str] = field(
        default_factory=lambda: _list("TOURIST_EMAIL_DOMAINS", "gmail.com,googlemail.com")
    )

    staff_max_failed_logins: int = field(default_factory=lambda: _int("STAFF_MAX_FAILED_LOGINS", 5))
    staff_lockout_minutes: int = field(default_factory=lambda: _int("STAFF_LOCKOUT_MINUTES", 15))

    email_provider: str = field(default_factory=lambda: os.getenv("EMAIL_PROVIDER", "none").lower())
    email_api_key: str = field(default_factory=lambda: os.getenv("EMAIL_API_KEY") or os.getenv("RESEND_API_KEY", ""))
    email_from: str = field(default_factory=lambda: os.getenv("EMAIL_FROM") or os.getenv("RESEND_FROM_EMAIL", ""))
    admin_alert_email: str = field(default_factory=lambda: os.getenv("ADMIN_ALERT_EMAIL", ""))
    expo_push_enabled: bool = field(default_factory=lambda: _bool("EXPO_PUSH_ENABLED", False))
    expo_access_token: str = field(default_factory=lambda: os.getenv("PUSH_NOTIFICATION_CREDENTIALS", ""))

    bootstrap_admin_email: str = field(default_factory=lambda: os.getenv("BOOTSTRAP_ADMIN_EMAIL", ""))
    bootstrap_admin_password: str = field(default_factory=lambda: os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""))
    seed_demo_staff: bool = field(default_factory=lambda: _bool("SEED_DEMO_STAFF", False))

    location_retention_days: int = field(default_factory=lambda: _int("LOCATION_RETENTION_DAYS", 30))
    caution_buffer_ratio: float = 1.5
    stale_location_minutes: int = field(default_factory=lambda: _int("STALE_LOCATION_MINUTES", 15))

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate(self) -> None:
        if self.is_production and self.secret_key == DEV_SECRET:
            raise RuntimeError("SECRET_KEY must be set in production")
        if self.is_production and len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
