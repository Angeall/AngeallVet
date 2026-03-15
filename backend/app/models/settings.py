from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class ClinicSettings(Base):
    __tablename__ = "clinic_settings"

    id = Column(Integer, primary_key=True, index=True)
    clinic_name = Column(String(255))
    address = Column(String(255))
    city = Column(String(100))
    postal_code = Column(String(10))
    country = Column(String(50), default="France")
    phone = Column(String(20))
    email = Column(String(255))
    siret = Column(String(20))
    ape_code = Column(String(10))
    vat_number = Column(String(50))
    logo_url = Column(String(500))
    default_appointment_duration_minutes = Column(Integer, default=30)
    debt_acknowledgment_template = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VatRate(Base):
    __tablename__ = "vat_rates"

    id = Column(Integer, primary_key=True, index=True)
    rate = Column(Numeric(5, 2), nullable=False)
    label = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
