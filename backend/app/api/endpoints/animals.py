from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.animal import Animal, AnimalAlert, WeightRecord
from app.schemas.animal import (
    AnimalCreate, AnimalUpdate, AnimalResponse,
    AnimalAlertCreate, AnimalAlertResponse,
    WeightRecordCreate, WeightRecordResponse,
)

router = APIRouter(prefix="/animals", tags=["Animals"])


@router.get("", response_model=list[AnimalResponse])
def list_animals(
    client_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Animal)
    if client_id:
        query = query.filter(Animal.client_id == client_id)
    if species:
        query = query.filter(Animal.species == species)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Animal.name.ilike(pattern),
                Animal.microchip_number.ilike(pattern),
                Animal.tattoo_number.ilike(pattern),
            )
        )
    return query.order_by(Animal.name).offset(skip).limit(limit).all()


@router.post("", response_model=AnimalResponse, status_code=201)
def create_animal(
    data: AnimalCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = Animal(**data.model_dump())
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return animal


@router.get("/{animal_id}", response_model=AnimalResponse)
def get_animal(
    animal_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouvé")
    return animal


@router.put("/{animal_id}", response_model=AnimalResponse)
def update_animal(
    animal_id: int,
    data: AnimalUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouvé")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(animal, field, value)

    db.commit()
    db.refresh(animal)
    return animal


# --- Alerts ---
@router.post("/{animal_id}/alerts", response_model=AnimalAlertResponse, status_code=201)
def add_alert(
    animal_id: int,
    data: AnimalAlertCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouvé")
    alert = AnimalAlert(animal_id=animal_id, **data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{animal_id}/alerts/{alert_id}", status_code=204)
def remove_alert(
    animal_id: int,
    alert_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.query(AnimalAlert).filter(
        AnimalAlert.id == alert_id, AnimalAlert.animal_id == animal_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    alert.is_active = False
    db.commit()


# --- Weight Records ---
@router.get("/{animal_id}/weights", response_model=list[WeightRecordResponse])
def get_weights(
    animal_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(WeightRecord)
        .filter(WeightRecord.animal_id == animal_id)
        .order_by(WeightRecord.recorded_at.desc())
        .all()
    )


@router.post("/{animal_id}/weights", response_model=WeightRecordResponse, status_code=201)
def add_weight(
    animal_id: int,
    data: WeightRecordCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouvé")
    record = WeightRecord(
        animal_id=animal_id,
        weight_kg=data.weight_kg,
        recorded_by_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
