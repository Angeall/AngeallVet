from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
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
    account_balance = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    merged_into_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    animals = relationship("Animal", back_populates="owner", lazy="selectin")
    invoices = relationship("Invoice", back_populates="client", lazy="dynamic")
