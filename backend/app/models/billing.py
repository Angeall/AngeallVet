from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, Date,
    ForeignKey, Enum as SAEnum, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), index=True)
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, index=True)
    issue_date = Column(Date, server_default=func.current_date(), index=True)
    due_date = Column(Date)
    subtotal = Column(Numeric(10, 2), default=0)
    total_vat = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    amount_paid = Column(Numeric(10, 2), default=0)
    notes = Column(Text)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), default=20.00)
    discount_percent = Column(Numeric(5, 2), default=0)
    line_total = Column(Numeric(10, 2))

    invoice = relationship("Invoice", back_populates="lines")


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    estimate_number = Column(String(50), unique=True, nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), index=True)
    status = Column(String(20), default="draft", index=True)  # draft, sent, accepted, rejected, invoiced
    issue_date = Column(Date, server_default=func.current_date())
    valid_until = Column(Date)
    subtotal = Column(Numeric(10, 2), default=0)
    total_vat = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    notes = Column(Text)
    client_signature = Column(Text)  # base64 signature
    signed_at = Column(DateTime(timezone=True))
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lines = relationship("EstimateLine", back_populates="estimate", cascade="all, delete-orphan")


class EstimateLine(Base):
    __tablename__ = "estimate_lines"

    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), default=20.00)
    line_total = Column(Numeric(10, 2))

    estimate = relationship("Estimate", back_populates="lines")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)  # cash, card, check, transfer, stripe
    payment_date = Column(Date, server_default=func.current_date())
    reference = Column(String(200))  # stripe payment id, check number, etc.
    notes = Column(Text)
    received_by_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="payments")
