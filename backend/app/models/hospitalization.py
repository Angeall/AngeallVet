from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class HospitalizationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISCHARGED = "discharged"
    DECEASED = "deceased"


class Hospitalization(Base):
    __tablename__ = "hospitalizations"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, index=True)
    veterinarian_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(HospitalizationStatus), default=HospitalizationStatus.ACTIVE)
    reason = Column(Text, nullable=False)
    admitted_at = Column(DateTime(timezone=True), server_default=func.now())
    discharged_at = Column(DateTime(timezone=True))
    cage_number = Column(String(20))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    care_tasks = relationship("CareTask", back_populates="hospitalization", order_by="CareTask.scheduled_at")


class CareTask(Base):
    __tablename__ = "care_tasks"

    id = Column(Integer, primary_key=True, index=True)
    hospitalization_id = Column(Integer, ForeignKey("hospitalizations.id"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    task_type = Column(String(50), nullable=False)  # medication, vitals, feeding, observation
    description = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))
    completed_by_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospitalization = relationship("Hospitalization", back_populates="care_tasks")
