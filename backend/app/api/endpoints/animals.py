from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.animal import Animal, AnimalAlert, WeightRecord, SpeciesRecord
from app.models.association import Association
from app.schemas.animal import (
    AnimalCreate, AnimalUpdate, AnimalResponse,
    AnimalAlertCreate, AnimalAlertResponse,
    WeightRecordCreate, WeightRecordResponse,
    SpeciesCreate, SpeciesResponse,
)

router = APIRouter(prefix="/animals", tags=["Animals"])


def _enrich_animal(animal):
    """Add association_name to animal object for serialization."""
    if animal.association_id and animal.association:
        animal.association_name = animal.association.name
    else:
        animal.association_name = None
    return animal


# --- Species ---
@router.get("/species", response_model=list[SpeciesResponse])
def list_species(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SpeciesRecord).filter(SpeciesRecord.is_active == True).order_by(SpeciesRecord.display_order, SpeciesRecord.label).all()


@router.post("/species", response_model=SpeciesResponse, status_code=201)
def create_species(
    data: SpeciesCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(SpeciesRecord).filter(SpeciesRecord.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce code espèce existe déjà")
    species = SpeciesRecord(**data.model_dump())
    db.add(species)
    db.commit()
    db.refresh(species)
    return species


@router.put("/species/{species_id}", response_model=SpeciesResponse)
def update_species(
    species_id: int,
    data: SpeciesCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    species = db.query(SpeciesRecord).filter(SpeciesRecord.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Espèce non trouvée")
    for field, value in data.model_dump().items():
        setattr(species, field, value)
    db.commit()
    db.refresh(species)
    return species


@router.delete("/species/{species_id}", status_code=204)
def delete_species(
    species_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    species = db.query(SpeciesRecord).filter(SpeciesRecord.id == species_id).first()
    if not species:
        raise HTTPException(status_code=404, detail="Espèce non trouvée")
    species.is_active = False
    db.commit()


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
    animals = query.order_by(Animal.name).offset(skip).limit(limit).all()
    return [_enrich_animal(a) for a in animals]


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
    return _enrich_animal(animal)


@router.get("/{animal_id}", response_model=AnimalResponse)
def get_animal(
    animal_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouvé")
    return _enrich_animal(animal)


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
    return _enrich_animal(animal)


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


@router.get("/{animal_id}/weights/latest", response_model=WeightRecordResponse)
def get_latest_weight(
    animal_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(WeightRecord)
        .filter(WeightRecord.animal_id == animal_id)
        .order_by(WeightRecord.recorded_at.desc(), WeightRecord.id.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Aucun poids enregistre")
    return record


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
