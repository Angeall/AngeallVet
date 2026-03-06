from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.animal import Species, Sex


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


class AnimalBase(BaseModel):
    name: str
    species: Species
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


class AnimalUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[Species] = None
    breed: Optional[str] = None
    sex: Optional[Sex] = None
    date_of_birth: Optional[date] = None
    color: Optional[str] = None
    microchip_number: Optional[str] = None
    tattoo_number: Optional[str] = None
    is_neutered: Optional[bool] = None
    is_deceased: Optional[bool] = None
    deceased_date: Optional[date] = None
    notes: Optional[str] = None


class AnimalResponse(AnimalBase):
    id: int
    client_id: int
    is_deceased: bool
    photo_url: Optional[str] = None
    created_at: datetime
    alerts: List[AnimalAlertResponse] = []

    class Config:
        from_attributes = True
