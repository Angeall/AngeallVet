from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.inventory import ProductType


class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductLotResponse(BaseModel):
    id: int
    lot_number: str
    expiry_date: date
    quantity: Decimal
    received_date: Optional[date] = None

    class Config:
        from_attributes = True


class ProductLotCreate(BaseModel):
    lot_number: str
    expiry_date: date
    quantity: Decimal


class ProductBase(BaseModel):
    name: str
    reference: Optional[str] = None
    product_type: ProductType
    description: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    selling_price: Decimal
    vat_rate: Decimal = Decimal("20.00")
    stock_alert_threshold: Decimal = Decimal("5")
    ean13: Optional[str] = None
    notes: Optional[str] = None
    requires_prescription: bool = False
    supplier_id: Optional[int] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ean13: Optional[str] = None
    notes: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    stock_alert_threshold: Optional[Decimal] = None
    requires_prescription: Optional[bool] = None
    is_active: Optional[bool] = None
    supplier_id: Optional[int] = None


class ProductResponse(ProductBase):
    id: int
    stock_quantity: Decimal
    is_active: bool
    lots: List[ProductLotResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class StockMovementCreate(BaseModel):
    product_id: int
    lot_id: Optional[int] = None
    movement_type: str  # in, out, adjustment
    quantity: Decimal
    reason: Optional[str] = None


class StockMovementResponse(StockMovementCreate):
    id: int
    performed_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Optional[Decimal] = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    notes: Optional[str] = None
    items: List[PurchaseOrderItemCreate] = []


class PurchaseOrderResponse(BaseModel):
    id: int
    order_number: str
    supplier_id: int
    status: str
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
