"""Configurable vaccination protocols + structured administrations
(the ``vaccine_protocols`` paid module — "vaccins avancés").

A **protocol** is an ordered series of **doses** for a species (puppy CHPPi
series, rabies, …). Each dose carries a valence and the interval (in days) from
the *previous* dose; the final dose may recur as an annual/triennial booster.

A **Vaccination** is one administration. When it is linked to a protocol dose,
the engine computes ``next_due_date`` (the next dose, or the recurring booster),
which drives the "due" list and the automated reminders.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class VaccineProtocol(Base):
    __tablename__ = "vaccine_protocols"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    species = Column(String(50))            # species code; null = all species
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doses = relationship(
        "VaccineProtocolDose", back_populates="protocol",
        cascade="all, delete-orphan", order_by="VaccineProtocolDose.sequence",
    )


class VaccineProtocolDose(Base):
    __tablename__ = "vaccine_protocol_doses"

    id = Column(Integer, primary_key=True)
    protocol_id = Column(Integer, ForeignKey("vaccine_protocols.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False, default=0)  # order within the protocol
    label = Column(String(120), nullable=False)            # "Primo 1", "Rappel annuel"…
    valence = Column(String(120))                          # "CHPPiL", "Rage"…
    interval_days = Column(Integer, default=0)             # days after the previous dose
    is_booster = Column(Boolean, default=False)            # recurring final dose
    booster_interval_days = Column(Integer)                # recurrence (e.g. 365, 1095)

    protocol = relationship("VaccineProtocol", back_populates="doses")


class Vaccination(Base):
    __tablename__ = "vaccinations"

    id = Column(Integer, primary_key=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, index=True)
    protocol_id = Column(Integer, ForeignKey("vaccine_protocols.id"), nullable=True, index=True)
    dose_id = Column(Integer, ForeignKey("vaccine_protocol_doses.id"), nullable=True)
    valence = Column(String(120), nullable=False)
    date_administered = Column(Date, nullable=False, index=True)
    lot_number = Column(String(100))
    veterinarian_id = Column(Integer, ForeignKey("users.id"), index=True)
    notes = Column(Text)
    # Computed schedule for the next dose / booster.
    next_due_date = Column(Date, index=True)
    next_label = Column(String(150))
    reminder_sent = Column(Boolean, default=False)  # dedup for the automated reminder
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    animal = relationship("Animal")
    protocol = relationship("VaccineProtocol")
