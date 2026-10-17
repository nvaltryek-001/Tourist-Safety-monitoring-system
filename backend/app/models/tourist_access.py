from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class TouristAccess(Base):
    __tablename__ = "tourist_access"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    tourist_code = Column(String(50), unique=True, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
