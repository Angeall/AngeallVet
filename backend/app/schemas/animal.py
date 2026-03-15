from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.animal import Sex, VitalStatus


class AnimalAlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    severity: str
    is_active: bool

    class Config:
        from_attributes = True


class AnimalAlertCreate(BaseModel):
    alert_type: str
    message: str
    severity: str = "warning"


class WeightRecordResponse(BaseModel):
    id: int
    weight_kg: Decimal
    recorded_at: datetime

    class Config:
        from_attributes = True


class WeightRecordCreate(BaseModel):
    weight_kg: Decimal


class SpeciesCreate(BaseModel):
    code: str
    label: str
    display_order: int = 0


class SpeciesResponse(SpeciesCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class AnimalBase(BaseModel):
    name: str
    species: str
    breed: Optional[str] = None
    sex: Sex = Sex.UNKNOWN
    date_of_birth: Optional[date] = None
    color: Optional[str] = None
    microchip_number: Optional[str] = None
    tattoo_number: Optional[str] = None
    is_neutered: bool = False
    notes: Optional[str] = None


class AnimalCreate(AnimalBase):
    client_id: int
    association_id: Optional[int] = None


class AnimalUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    breed: Optional[str] = None
    sex: Optional[Sex] = None
    date_of_birth: Optional[date] = None
    color: Optional[str] = None
    microchip_number: Optional[str] = None
    tattoo_number: Optional[str] = None
    is_neutered: Optional[bool] = None
    vital_status: Optional[VitalStatus] = None
    vital_status_date: Optional[date] = None
    is_deceased: Optional[bool] = None
    deceased_date: Optional[date] = None
    association_id: Optional[int] = None
    notes: Optional[str] = None


class AnimalResponse(AnimalBase):
    id: int
    client_id: int
    vital_status: VitalStatus = VitalStatus.ALIVE
    vital_status_date: Optional[date] = None
    association_id: Optional[int] = None
    association_name: Optional[str] = None
    is_deceased: bool
    photo_url: Optional[str] = None
    created_at: datetime
    alerts: List[AnimalAlertResponse] = []

    class Config:
        from_attributes = True
