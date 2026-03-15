from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class CommunicationCreate(BaseModel):
    client_id: int
    channel: Literal["email", "sms", "postal"]
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
    reminder_type: Literal["vaccine", "antiparasitic", "checkup"]
    species: Optional[str] = None
    channel: Literal["email", "sms", "both", "postal"] = "email"
    days_before: int = 30
    days_before_second: int = 7
    days_after: int = 1
    email_template: Optional[str] = None
    sms_template: Optional[str] = None
    postal_template: Optional[str] = None


class ReminderRuleResponse(BaseModel):
    id: int
    name: str
    reminder_type: str
    species: Optional[str] = None
    channel: str = "email"
    days_before: int = 30
    days_before_second: int = 7
    days_after: int = 1
    email_template: Optional[str] = None
    sms_template: Optional[str] = None
    postal_template: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
