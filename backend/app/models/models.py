from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


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


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(Integer, primary_key=True, index=True)
    tourist_code = Column(String(50), index=True, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="OPEN", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
