import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from typing import Optional
from datetime import date
from decimal import Decimal

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.inventory import Product
from app.models.animal import Animal
from app.models.client import Client
from app.models.controlled_substance import ControlledSubstanceEntry
from app.schemas.controlled_substance import (
    ControlledSubstanceEntryCreate, ControlledSubstanceEntryResponse,
)

router = APIRouter(prefix="/controlled-substances", tags=["Controlled Substances"])


def _enrich_entry(entry, db):
    """Build a ControlledSubstanceEntryResponse with resolved names."""
    product = db.query(Product).filter(Product.id == entry.product_id).first()
    vet_name = None
    if entry.prescribing_vet_id:
        vet = db.query(User).filter(User.id == entry.prescribing_vet_id).first()
        if vet:
            vet_name = f"{vet.first_name} {vet.last_name}"
    animal_name = None
    client_name = None
    if entry.patient_animal_id:
        animal = db.query(Animal).filter(Animal.id == entry.patient_animal_id).first()
        if animal:
            animal_name = animal.name
            client = db.query(Client).filter(Client.id == animal.client_id).first()
            if client:
                client_name = f"{client.last_name} {client.first_name}"
    return ControlledSubstanceEntryResponse(
        id=entry.id,
        product_id=entry.product_id,
        product_name=product.name if product else None,
        date=entry.date,
        movement_type=entry.movement_type,
        quantity=entry.quantity,
        lot_number=entry.lot_number,
        patient_animal_id=entry.patient_animal_id,
        patient_animal_name=animal_name,
        patient_owner_name=entry.patient_owner_name,
        patient_client_name=client_name,
        prescribing_vet_id=entry.prescribing_vet_id,
        prescribing_vet_name=vet_name,
        reason=entry.reason,
        dosage=entry.dosage,
        total_delivered=entry.total_delivered,
        remaining_stock=entry.remaining_stock,
        notes=entry.notes,
        created_at=entry.created_at,
    )


@router.get("/register", response_model=list[ControlledSubstanceEntryResponse])
def list_register(
    product_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ControlledSubstanceEntry)
    if product_id:
        query = query.filter(ControlledSubstanceEntry.product_id == product_id)
    if date_from:
        query = query.filter(ControlledSubstanceEntry.date >= date_from)
    if date_to:
        query = query.filter(ControlledSubstanceEntry.date <= date_to)

    entries = query.order_by(
        ControlledSubstanceEntry.date.desc(),
        ControlledSubstanceEntry.id.desc(),
    ).offset(skip).limit(limit).all()

    return [_enrich_entry(e, db) for e in entries]


@router.post("/entries", response_model=ControlledSubstanceEntryResponse, status_code=201)
def create_entry(
    data: ControlledSubstanceEntryCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    if not product.is_controlled_substance:
        raise HTTPException(status_code=400, detail="Ce produit n'est pas une substance contrôlée")

    # Calculate remaining stock
    last_entry = (
        db.query(ControlledSubstanceEntry)
        .filter(ControlledSubstanceEntry.product_id == data.product_id)
        .order_by(ControlledSubstanceEntry.id.desc())
        .first()
    )
    previous_stock = Decimal(str(last_entry.remaining_stock)) if last_entry else Decimal("0")

    if data.movement_type == "in":
        remaining = previous_stock + data.quantity
    else:
        remaining = previous_stock - data.quantity

    entry = ControlledSubstanceEntry(
        product_id=data.product_id,
        date=data.date or date.today(),
        movement_type=data.movement_type,
        quantity=data.quantity,
        lot_number=data.lot_number,
        patient_animal_id=data.patient_animal_id,
        patient_owner_name=data.patient_owner_name,
        prescribing_vet_id=data.prescribing_vet_id or current_user.id,
        reason=data.reason,
        dosage=data.dosage,
        total_delivered=data.total_delivered,
        remaining_stock=remaining,
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return _enrich_entry(entry, db)


@router.get("/register/export")
def export_register(
    product_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Export the controlled substances register as CSV."""
    query = db.query(ControlledSubstanceEntry)
    if product_id:
        query = query.filter(ControlledSubstanceEntry.product_id == product_id)
    if date_from:
        query = query.filter(ControlledSubstanceEntry.date >= date_from)
    if date_to:
        query = query.filter(ControlledSubstanceEntry.date <= date_to)

    entries = query.order_by(
        ControlledSubstanceEntry.date.asc(),
        ControlledSubstanceEntry.id.asc(),
    ).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Date", "Produit", "Type", "Quantité", "N° Lot",
        "Animal/Patient", "Propriétaire", "Vétérinaire", "Motif",
        "Stock restant", "Notes",
    ])

    for entry in entries:
        product = db.query(Product).filter(Product.id == entry.product_id).first()
        vet_name = ""
        if entry.prescribing_vet_id:
            vet = db.query(User).filter(User.id == entry.prescribing_vet_id).first()
            if vet:
                vet_name = f"{vet.first_name} {vet.last_name}"
        animal_name = ""
        if entry.patient_animal_id:
            animal = db.query(Animal).filter(Animal.id == entry.patient_animal_id).first()
            if animal:
                animal_name = animal.name

        type_labels = {"in": "Entrée", "out": "Sortie", "destruction": "Destruction", "prescription": "Prescription"}
        writer.writerow([
            entry.date.isoformat() if entry.date else "",
            product.name if product else str(entry.product_id),
            type_labels.get(entry.movement_type, entry.movement_type),
            str(entry.quantity),
            entry.lot_number or "",
            animal_name,
            entry.patient_owner_name or "",
            vet_name,
            entry.reason or "",
            str(entry.remaining_stock),
            entry.notes or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=registre_stupefiants.csv"},
    )
