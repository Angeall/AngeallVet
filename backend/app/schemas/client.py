from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


def _empty_to_none(v):
    """Convert empty strings to None so Optional fields pass validation."""
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


class ClientBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "France"
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None
    vat_number: Optional[str] = None

    @field_validator("email", "phone", "mobile", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notes: Optional[str] = None
    vat_number: Optional[str] = None

    @field_validator("email", "phone", "mobile", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        return _empty_to_none(v)


class ClientAlertCreate(BaseModel):
    alert_type: str
    message: str
    severity: str = "warning"


class ClientAlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    severity: str
    is_active: bool

    class Config:
        from_attributes = True


class ClientResponse(ClientBase):
    id: int
    account_balance: Decimal
    is_active: bool
    created_at: datetime
    animal_count: Optional[int] = None
    vat_number: Optional[str] = None
    alerts: List[ClientAlertResponse] = []

    class Config:
        from_attributes = True


class ClientNoteCreate(BaseModel):
    content: str
    source: str = "manual"  # manual, appointment


class ClientNoteResponse(BaseModel):
    id: int
    client_id: int
    content: str
    source: str = "manual"
    created_by_id: int
    created_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClientMergeRequest(BaseModel):
    source_client_id: int
    target_client_id: int
