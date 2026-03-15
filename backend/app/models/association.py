from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class Association(Base):
    __tablename__ = "associations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact_name = Column(String(200))
    email = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    discount_percent = Column(Numeric(5, 2), default=0)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
