from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal


class ControlledSubstanceEntryCreate(BaseModel):
    product_id: int
    date: Optional[date] = None
    movement_type: Literal["in", "out", "destruction", "prescription"]
    quantity: Decimal = Field(..., gt=0)
    lot_number: Optional[str] = None
    patient_animal_id: Optional[int] = None
    patient_owner_name: Optional[str] = None
    prescribing_vet_id: Optional[int] = None
    reason: Optional[str] = None
    dosage: Optional[str] = None
    total_delivered: Optional[Decimal] = None
    notes: Optional[str] = None


class ControlledSubstanceEntryResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    date: date
    movement_type: str
    quantity: Decimal
    lot_number: Optional[str] = None
    patient_animal_id: Optional[int] = None
    patient_animal_name: Optional[str] = None
    patient_owner_name: Optional[str] = None
    patient_client_name: Optional[str] = None
    prescribing_vet_id: Optional[int] = None
    prescribing_vet_name: Optional[str] = None
    reason: Optional[str] = None
    dosage: Optional[str] = None
    total_delivered: Optional[Decimal] = None
    remaining_stock: Decimal
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
