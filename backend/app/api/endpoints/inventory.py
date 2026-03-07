from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, timedelta
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.inventory import (
    Product, ProductLot, StockMovement, Supplier,
    PurchaseOrder, PurchaseOrderItem,
)
from app.schemas.inventory import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductLotCreate, ProductLotResponse,
    StockMovementCreate, StockMovementResponse,
    SupplierCreate, SupplierResponse,
    PurchaseOrderCreate, PurchaseOrderResponse,
)

router = APIRouter(prefix="/inventory", tags=["Inventory & Pharmacy"])


# --- Products ---
@router.get("/products", response_model=list[ProductResponse])
def list_products(
    search: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    low_stock: bool = Query(False),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Product).filter(Product.is_active == True)
    if search:
        pattern = f"%{search}%"
        query = query.filter(Product.name.ilike(pattern))
    if product_type:
        query = query.filter(Product.product_type == product_type)
    if low_stock:
        query = query.filter(Product.stock_quantity <= Product.stock_alert_threshold)
    return query.order_by(Product.name).offset(skip).limit(limit).all()


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.reference:
        data.reference = f"PRD-{uuid.uuid4().hex[:8].upper()}"
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


# --- Lots ---
@router.post("/products/{product_id}/lots", response_model=ProductLotResponse, status_code=201)
def add_lot(
    product_id: int,
    data: ProductLotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    lot = ProductLot(product_id=product_id, **data.model_dump())
    db.add(lot)

    # Update total stock
    product.stock_quantity = (product.stock_quantity or 0) + data.quantity

    # Record movement
    movement = StockMovement(
        product_id=product_id,
        movement_type="in",
        quantity=data.quantity,
        reason=f"Réception lot {data.lot_number}",
        reference_type="lot",
        performed_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(lot)
    return lot


@router.get("/expiring", response_model=list[ProductLotResponse])
def get_expiring_lots(
    days: int = Query(30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    threshold = date.today() + timedelta(days=days)
    return (
        db.query(ProductLot)
        .filter(
            ProductLot.expiry_date <= threshold,
            ProductLot.quantity > 0,
        )
        .order_by(ProductLot.expiry_date)
        .all()
    )


# --- Stock Movements ---
@router.post("/movements", response_model=StockMovementResponse, status_code=201)
def create_movement(
    data: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")

    if data.movement_type == "in":
        product.stock_quantity = (product.stock_quantity or 0) + data.quantity
    elif data.movement_type == "out":
        if (product.stock_quantity or 0) < data.quantity:
            raise HTTPException(status_code=400, detail="Stock insuffisant")
        product.stock_quantity = (product.stock_quantity or 0) - data.quantity
    else:  # adjustment
        product.stock_quantity = data.quantity

    movement = StockMovement(
        **data.model_dump(),
        performed_by_id=current_user.id,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


# --- Suppliers ---
@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


# --- Purchase Orders ---
@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order(
    data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
    order = PurchaseOrder(
        supplier_id=data.supplier_id,
        order_number=order_number,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(order)
    db.flush()

    total = 0
    for item_data in data.items:
        item = PurchaseOrderItem(
            order_id=order.id,
            **item_data.model_dump(),
        )
        db.add(item)
        if item_data.unit_price:
            total += item_data.quantity * item_data.unit_price

    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order


@router.get("/alerts", response_model=list[ProductResponse])
def get_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Product)
        .filter(
            Product.is_active == True,
            Product.stock_quantity <= Product.stock_alert_threshold,
            Product.product_type != "service",
        )
        .order_by(Product.stock_quantity)
        .all()
    )
