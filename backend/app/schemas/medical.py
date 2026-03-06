from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.medical import RecordType


class AttachmentResponse(BaseModel):
    id: int
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    description: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PrescriptionItemCreate(BaseModel):
    product_id: Optional[int] = None
    medication_name: str
    dosage: Optional[str] = None
    dosage_per_kg: Optional[Decimal] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    quantity: Optional[Decimal] = None
    instructions: Optional[str] = None


class PrescriptionItemResponse(PrescriptionItemCreate):
    id: int

    class Config:
        from_attributes = True


class PrescriptionCreate(BaseModel):
    notes: Optional[str] = None
    items: List[PrescriptionItemCreate] = []


class PrescriptionResponse(BaseModel):
    id: int
    prescription_date: date
    notes: Optional[str] = None
    items: List[PrescriptionItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MedicalRecordBase(BaseModel):
    animal_id: int
    record_type: RecordType
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    notes: Optional[str] = None
    template_id: Optional[int] = None
    appointment_id: Optional[int] = None


class MedicalRecordCreate(MedicalRecordBase):
    prescriptions: List[PrescriptionCreate] = []


class MedicalRecordResponse(MedicalRecordBase):
    id: int
    veterinarian_id: int
    prescriptions: List[PrescriptionResponse] = []
    attachments: List[AttachmentResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ConsultationTemplateCreate(BaseModel):
    name: str
    category: Optional[str] = None
    species: Optional[str] = None
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None


class ConsultationTemplateResponse(ConsultationTemplateCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
