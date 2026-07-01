from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.billing import InvoiceStatus


class InvoiceLineCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal = Field(Decimal("1"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(Decimal("20.00"), ge=0, le=100)
    discount_percent: Decimal = Field(Decimal("0"), ge=0, le=100)
    lot_number: Optional[str] = None


class InvoiceLineResponse(InvoiceLineCreate):
    id: int
    line_total: Optional[Decimal] = None

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    client_id: int
    animal_id: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[InvoiceLineCreate] = []


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class InvoiceVeterinarianResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    animal_id: Optional[int] = None
    status: InvoiceStatus
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Decimal
    total_vat: Decimal
    total: Decimal
    amount_paid: Decimal
    notes: Optional[str] = None
    lines: List[InvoiceLineResponse] = []
    payments: List["PaymentResponse"] = []
    veterinarians: List[InvoiceVeterinarianResponse] = []
    created_at: datetime
    client_name: Optional[str] = None
    invoice_ninja_invoice_id: Optional[str] = None

    class Config:
        from_attributes = True


class EstimateLineCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal = Field(Decimal("1"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal = Field(Decimal("20.00"), ge=0, le=100)


class EstimateLineResponse(EstimateLineCreate):
    id: int
    line_total: Optional[Decimal] = None

    class Config:
        from_attributes = True


class EstimateCreate(BaseModel):
    client_id: int
    animal_id: Optional[int] = None
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    lines: List[EstimateLineCreate] = []


class EstimateResponse(BaseModel):
    id: int
    estimate_number: str
    client_id: int
    animal_id: Optional[int] = None
    status: str
    issue_date: Optional[date] = None
    valid_until: Optional[date] = None
    subtotal: Decimal
    total_vat: Decimal
    total: Decimal
    notes: Optional[str] = None
    lines: List[EstimateLineResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    payment_method: str
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    payment_method: str
    reference: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EstimateToInvoiceRequest(BaseModel):
    estimate_id: int


# Resolve forward reference for InvoiceResponse.payments
InvoiceResponse.model_rebuild()
