from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CommunicationCreate(BaseModel):
    client_id: int
    channel: str  # email, sms
    subject: Optional[str] = None
    body: str


class CommunicationResponse(BaseModel):
    id: int
    client_id: int
    channel: str
    subject: Optional[str] = None
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderRuleCreate(BaseModel):
    name: str
    reminder_type: str
    species: Optional[str] = None
    channel: str = "email"
    days_before: int = 30
    days_before_second: int = 7
    days_after: int = 1
    email_template: Optional[str] = None
    sms_template: Optional[str] = None


class ReminderRuleResponse(ReminderRuleCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
