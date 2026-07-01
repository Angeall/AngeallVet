from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ClinicSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    ape_code: Optional[str] = None
    vat_number: Optional[str] = None
    logo_url: Optional[str] = None
    default_appointment_duration_minutes: Optional[int] = None
    allow_cross_vet_invoice_edit: Optional[bool] = None
    debt_acknowledgment_template: Optional[str] = None
    invoice_ninja_url: Optional[str] = None
    invoice_ninja_token: Optional[str] = None


class ClinicSettingsResponse(BaseModel):
    id: int
    clinic_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    ape_code: Optional[str] = None
    vat_number: Optional[str] = None
    logo_url: Optional[str] = None
    default_appointment_duration_minutes: Optional[int] = 30
    allow_cross_vet_invoice_edit: bool = True
    debt_acknowledgment_template: Optional[str] = None
    invoice_ninja_url: Optional[str] = None
    invoice_ninja_token_set: bool = False
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VatRateCreate(BaseModel):
    rate: Decimal
    label: str
    is_default: bool = False


class VatRateUpdate(BaseModel):
    rate: Optional[Decimal] = None
    label: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class VatRateResponse(BaseModel):
    id: int
    rate: Decimal
    label: str
    is_default: bool
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
