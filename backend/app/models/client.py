from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), index=True)
    phone = Column(String(20))
    mobile = Column(String(20))
    address = Column(String(255))
    city = Column(String(100))
    postal_code = Column(String(10))
    country = Column(String(50), default="France")
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    notes = Column(Text)
    vat_number = Column(String(50))
    account_balance = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    merged_into_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    animals = relationship("Animal", back_populates="owner", lazy="selectin")
    invoices = relationship("Invoice", back_populates="client", lazy="dynamic")
    alerts = relationship("ClientAlert", back_populates="client", lazy="selectin")


class ClientAlert(Base):
    __tablename__ = "client_alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # bad_payer, aggressive, other
    message = Column(String(500), nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, danger
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="alerts")
