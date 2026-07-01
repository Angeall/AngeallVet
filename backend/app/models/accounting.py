"""Cash register closing + cash journal (the ``accounting`` paid module).

A **closing** (clôture de caisse / Z-report) finalises one business day: it
aggregates the day's payments by method, reconciles the counted cash against the
expected cash (opening fund + cash in − cash out), and **locks the day** so no
payment or cash movement can be recorded on it afterwards (audit integrity).

A **cash movement** is a manual cash in/out not tied to an invoice (opening fund
top-up, transfer to the bank, petty-cash expense…).
"""
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, JSON,
)
from sqlalchemy.sql import func

from app.core.database import Base


class CashRegisterClosing(Base):
    __tablename__ = "cash_register_closings"

    id = Column(Integer, primary_key=True)
    business_date = Column(Date, nullable=False, unique=True, index=True)  # one per day
    opening_amount = Column(Numeric(10, 2), default=0)   # fond de caisse
    counted_amount = Column(Numeric(10, 2), default=0)   # espèces comptées
    expected_amount = Column(Numeric(10, 2), default=0)  # attendu en caisse (calculé)
    discrepancy = Column(Numeric(10, 2), default=0)      # counted − expected
    total_amount = Column(Numeric(10, 2), default=0)     # total encaissé du jour (tous moyens)
    payment_count = Column(Integer, default=0)
    totals_by_method = Column(JSON)                      # {"cash": .., "card": ..}
    notes = Column(Text)
    closed_by_id = Column(Integer, ForeignKey("users.id"))
    closed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CashMovement(Base):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True)
    business_date = Column(Date, nullable=False, index=True, server_default=func.current_date())
    direction = Column(String(3), nullable=False)  # in | out
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(255))
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
