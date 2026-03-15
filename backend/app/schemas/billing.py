from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.billing import InvoiceStatus


class InvoiceLineCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    vat_rate: Decimal = Decimal("20.00")
    discount_percent: Decimal = Decimal("0")
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

    class Config:
        from_attributes = True


class EstimateLineCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    vat_rate: Decimal = Decimal("20.00")


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
    amount: Decimal
    payment_method: str
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(PaymentCreate):
    id: int
    payment_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EstimateToInvoiceRequest(BaseModel):
    estimate_id: int


# Resolve forward reference for InvoiceResponse.payments
InvoiceResponse.model_rebuild()
