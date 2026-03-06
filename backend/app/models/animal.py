from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime,
    Boolean, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class Species(str, enum.Enum):
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    RABBIT = "rabbit"
    REPTILE = "reptile"
    HORSE = "horse"
    NAC = "nac"  # Nouveaux Animaux de Compagnie
    OTHER = "other"


class Sex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class Animal(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    species = Column(SAEnum(Species), nullable=False)
    breed = Column(String(100))
    sex = Column(SAEnum(Sex), default=Sex.UNKNOWN)
    date_of_birth = Column(Date)
    color = Column(String(100))
    microchip_number = Column(String(50), unique=True, index=True)
    tattoo_number = Column(String(50), index=True)
    is_neutered = Column(Boolean, default=False)
    is_deceased = Column(Boolean, default=False)
    deceased_date = Column(Date)
    photo_url = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("Client", back_populates="animals")
    alerts = relationship("AnimalAlert", back_populates="animal", lazy="selectin")
    weight_records = relationship("WeightRecord", back_populates="animal", order_by="WeightRecord.recorded_at.desc()")
    medical_records = relationship("MedicalRecord", back_populates="animal", order_by="MedicalRecord.created_at.desc()")


class AnimalAlert(Base):
    __tablename__ = "animal_alerts"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # aggressive, allergy, chronic_disease, other
    message = Column(String(500), nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, danger
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    animal = relationship("Animal", back_populates="alerts")


class WeightRecord(Base):
    __tablename__ = "weight_records"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, index=True)
    weight_kg = Column(Numeric(6, 2), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    recorded_by_id = Column(Integer, ForeignKey("users.id"))

    animal = relationship("Animal", back_populates="weight_records")
