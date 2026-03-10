from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean,
)
from sqlalchemy.sql import func

from app.core.database import Base


class Communication(Base):
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # email, sms
    subject = Column(String(500))
    body = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, sent, failed, delivered
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReminderRule(Base):
    __tablename__ = "reminder_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    reminder_type = Column(String(50), nullable=False)  # vaccine, antiparasitic, checkup
    species = Column(String(50))  # filter by species or null for all
    channel = Column(String(20), default="email")  # email, sms, both
    days_before = Column(Integer, default=30)  # J-30
    days_before_second = Column(Integer, default=7)  # J-7
    days_after = Column(Integer, default=1)  # J+1 if not done
    email_template = Column(Text)
    sms_template = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("reminder_rules.id"))
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), default="sent")  # sent, failed
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    next_due_date = Column(DateTime(timezone=True))
