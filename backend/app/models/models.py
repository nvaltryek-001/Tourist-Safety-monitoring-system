"""Database models.

The first three tables (tourists, safety_zones, sos_alerts) are the original
schema. Every column added later is nullable or has a server default so the
additive migration in ``app.migrations`` can upgrade an existing database
in place without touching existing rows.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------- original
class Tourist(Base):
    __tablename__ = "tourists"

    id = Column(Integer, primary_key=True, index=True)
    tourist_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    enrollment_number = Column(String(50), nullable=True, unique=True)
    college_email = Column(String(255), nullable=True, unique=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_email = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    safety_status = Column(String(20), default="SAFE", nullable=False)
    last_location_update = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    # added in schema v2
    location_accuracy = Column(Float, nullable=True)
    location_consent_at = Column(DateTime(timezone=True), nullable=True)
    expo_push_token = Column(String(255), nullable=True)
    notify_push = Column(Boolean, nullable=True, default=True)
    notify_email = Column(Boolean, nullable=True, default=True)


class SafetyZone(Base):
    __tablename__ = "safety_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Float, nullable=False)
    zone_type = Column(String(30), nullable=False, default="SAFE")
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    # added in schema v2
    risk_level = Column(String(20), nullable=True)  # LOW / MEDIUM / HIGH
    geometry_geojson = Column(Text, nullable=True)  # optional Polygon/MultiPolygon
    source = Column(String(255), nullable=True)
    verification_status = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=True, default=utc_now, onupdate=utc_now)


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tourist_code = Column(String(50), index=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="OPEN", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    # added in schema v2
    accuracy = Column(Float, nullable=True)
    alert_type = Column(String(30), nullable=True, default="GENERAL")
    idempotency_key = Column(String(80), nullable=True)
    assigned_officer_id = Column(Integer, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_outcome = Column(String(40), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, default=utc_now, onupdate=utc_now)


# --------------------------------------------------------------- schema v2
class StaffUser(Base):
    __tablename__ = "staff_users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # SUPER_ADMIN / ADMIN / POLICE
    password_hash = Column(String(255), nullable=False)
    badge_number = Column(String(50), nullable=True)
    station = Column(String(120), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    subject = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class LocationPoint(Base):
    __tablename__ = "location_history"
    __table_args__ = (Index("ix_location_history_tourist_time", "tourist_code", "recorded_at"),)

    id = Column(Integer, primary_key=True)
    tourist_code = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    safety_status = Column(String(20), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    received_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    client_id = Column(String(80), nullable=True)  # de-duplicates offline-queue replays


class GeofenceEvent(Base):
    __tablename__ = "geofence_events"
    __table_args__ = (Index("ix_geofence_events_tourist_time", "tourist_code", "created_at"),)

    id = Column(Integer, primary_key=True)
    tourist_code = Column(String(50), nullable=False)
    zone_id = Column(Integer, nullable=False, index=True)
    zone_name = Column(String(100), nullable=True)
    zone_type = Column(String(30), nullable=True)
    event_type = Column(String(10), nullable=False)  # ENTER / EXIT
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    tourist_code = Column(String(50), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    destination = Column(String(200), nullable=True)
    planned_end_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE / COMPLETED / CANCELLED
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True)
    sos_id = Column(Integer, ForeignKey("sos_alerts.id"), nullable=False, index=True)
    actor_type = Column(String(20), nullable=False)  # TOURIST / STAFF / SYSTEM
    actor_id = Column(String(255), nullable=True)
    actor_name = Column(String(120), nullable=True)
    action = Column(String(40), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),)

    id = Column(Integer, primary_key=True)
    recipient_type = Column(String(20), nullable=False)  # TOURIST / STAFF / CONTACT
    recipient_id = Column(String(255), nullable=True, index=True)
    channel = Column(String(20), nullable=False)  # IN_APP / PUSH / EMAIL / SMS
    category = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(255), nullable=True)
    dedupe_key = Column(String(160), nullable=True)
    related_sos_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    read_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(String(255), nullable=True)
    action = Column(String(60), nullable=False, index=True)
    target = Column(String(120), nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    note = Column(String(255), nullable=True)
