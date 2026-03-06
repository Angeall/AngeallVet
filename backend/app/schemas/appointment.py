from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.appointment import AppointmentType, AppointmentStatus


class AppointmentBase(BaseModel):
    client_id: int
    animal_id: Optional[int] = None
    veterinarian_id: int
    appointment_type: AppointmentType = AppointmentType.CONSULTATION
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None
    color_code: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    client_id: Optional[int] = None
    animal_id: Optional[int] = None
    veterinarian_id: Optional[int] = None
    appointment_type: Optional[AppointmentType] = None
    status: Optional[AppointmentStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    color_code: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: int
    status: AppointmentStatus
    google_event_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WaitingRoomUpdate(BaseModel):
    status: AppointmentStatus
