from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, Date,
    ForeignKey, Enum as SAEnum, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ProductType(str, enum.Enum):
    MEDICATION = "medication"
    FOOD = "food"
    SUPPLY = "supply"
    SERVICE = "service"  # Acte médical


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    reference = Column(String(100), unique=True, index=True)
    product_type = Column(SAEnum(ProductType), nullable=False)
    description = Column(Text)
    unit = Column(String(50))  # comprimé, ml, kg, unité
    purchase_price = Column(Numeric(10, 2))
    selling_price = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(4, 2), default=20.00)  # TVA %
    stock_quantity = Column(Numeric(10, 2), default=0)
    stock_alert_threshold = Column(Numeric(10, 2), default=5)
    ean13 = Column(String(13))
    notes = Column(Text)
    requires_prescription = Column(Boolean, default=False)
    is_shortcut = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lots = relationship("ProductLot", back_populates="product")
    supplier = relationship("Supplier", back_populates="products")


class ProductLot(Base):
    __tablename__ = "product_lots"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    lot_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    quantity = Column(Numeric(10, 2), nullable=False)
    received_date = Column(Date, server_default=func.current_date())

    product = relationship("Product", back_populates="lots")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    lot_id = Column(Integer, ForeignKey("product_lots.id"))
    movement_type = Column(String(20), nullable=False)  # in, out, adjustment
    quantity = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(200))
    reference_type = Column(String(50))  # invoice, prescription, manual
    reference_id = Column(Integer)
    performed_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact_name = Column(String(200))
    email = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="draft")  # draft, sent, received, cancelled
    total_amount = Column(Numeric(10, 2))
    notes = Column(Text)
    ordered_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("PurchaseOrderItem", back_populates="order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2))

    order = relationship("PurchaseOrder", back_populates="items")
