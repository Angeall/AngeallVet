from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, Date, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ControlledSubstanceEntry(Base):
    __tablename__ = "controlled_substance_entries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, server_default=func.current_date(), index=True)
    movement_type = Column(String(20), nullable=False)  # in, out, destruction, prescription
    quantity = Column(Numeric(10, 2), nullable=False)
    lot_number = Column(String(100))
    patient_animal_id = Column(Integer, ForeignKey("animals.id"), nullable=True, index=True)
    patient_owner_name = Column(String(200))
    prescribing_vet_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reason = Column(String(500))
    dosage = Column(String(200))  # ex: "0.5 mg/kg"
    total_delivered = Column(Numeric(10, 2))  # dose totale delivree
    remaining_stock = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product")
    animal = relationship("Animal")
