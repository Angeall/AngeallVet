from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.hospitalization import HospitalizationStatus


class CareTaskCreate(BaseModel):
    scheduled_at: datetime
    task_type: str
    description: str
    is_completed: Optional[bool] = False


class CareTaskUpdate(BaseModel):
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


class CareTaskResponse(BaseModel):
    id: int
    scheduled_at: datetime
    task_type: str
    description: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    completed_by_id: Optional[int] = None
    completed_by_name: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class HospitalizationCreate(BaseModel):
    animal_id: int
    reason: str
    cage_number: Optional[str] = None
    notes: Optional[str] = None
    care_tasks: List[CareTaskCreate] = []


class HospitalizationUpdate(BaseModel):
    status: Optional[HospitalizationStatus] = None
    cage_number: Optional[str] = None
    notes: Optional[str] = None


class HospitalizationResponse(BaseModel):
    id: int
    animal_id: int
    veterinarian_id: int
    status: HospitalizationStatus
    reason: str
    admitted_at: datetime
    discharged_at: Optional[datetime] = None
    cage_number: Optional[str] = None
    notes: Optional[str] = None
    care_tasks: List[CareTaskResponse] = []
    created_at: datetime
    animal_name: Optional[str] = None
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    veterinarian_name: Optional[str] = None

    class Config:
        from_attributes = True
