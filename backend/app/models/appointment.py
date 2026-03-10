from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AppointmentType(str, enum.Enum):
    CONSULTATION = "consultation"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    VACCINATION = "vaccination"
    CHECKUP = "checkup"
    GROOMING = "grooming"
    OTHER = "other"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    ARRIVED = "arrived"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), index=True)
    veterinarian_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_type = Column(SAEnum(AppointmentType), nullable=False, default=AppointmentType.CONSULTATION)
    status = Column(SAEnum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text)
    notes = Column(Text)
    color_code = Column(String(7))  # hex color
    google_event_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
