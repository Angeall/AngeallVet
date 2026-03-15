from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.hospitalization import Hospitalization, CareTask, HospitalizationStatus
from app.models.animal import Animal
from app.models.client import Client
from app.schemas.hospitalization import (
    HospitalizationCreate, HospitalizationUpdate, HospitalizationResponse,
    CareTaskCreate, CareTaskUpdate, CareTaskResponse,
)

router = APIRouter(prefix="/hospitalization", tags=["Hospitalization"])


def _enrich_hospitalization(hosp, db):
    """Add animal_name, client_name, veterinarian_name, and task completed_by_name."""
    data = HospitalizationResponse.model_validate(hosp).model_dump()
    animal = db.query(Animal).filter(Animal.id == hosp.animal_id).first()
    if animal:
        data["animal_name"] = animal.name
        data["client_id"] = animal.client_id
        client = db.query(Client).filter(Client.id == animal.client_id).first()
        if client:
            data["client_name"] = f"{client.last_name} {client.first_name}"
    vet = db.query(User).filter(User.id == hosp.veterinarian_id).first()
    if vet:
        data["veterinarian_name"] = f"Dr. {vet.last_name}"
    # Enrich care tasks with completed_by_name
    for task in data.get("care_tasks", []):
        if task.get("completed_by_id"):
            user = db.query(User).filter(User.id == task["completed_by_id"]).first()
            if user:
                task["completed_by_name"] = f"{user.first_name} {user.last_name}"
    return data


@router.get("", response_model=list[HospitalizationResponse])
def list_hospitalizations(
    active_only: bool = Query(True),
    animal_id: Optional[int] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Hospitalization)
    if active_only:
        query = query.filter(Hospitalization.status == HospitalizationStatus.ACTIVE)
    if animal_id is not None:
        query = query.filter(Hospitalization.animal_id == animal_id)
    hosps = query.order_by(Hospitalization.admitted_at.desc()).all()
    return [_enrich_hospitalization(h, db) for h in hosps]


@router.post("", response_model=HospitalizationResponse, status_code=201)
def create_hospitalization(
    data: HospitalizationCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    hosp = Hospitalization(
        animal_id=data.animal_id,
        veterinarian_id=current_user.id,
        reason=data.reason,
        cage_number=data.cage_number,
        notes=data.notes,
    )
    db.add(hosp)
    db.flush()

    for task_data in data.care_tasks:
        task = CareTask(
            hospitalization_id=hosp.id,
            **task_data.model_dump(),
        )
        db.add(task)

    db.commit()
    db.refresh(hosp)
    return _enrich_hospitalization(hosp, db)


@router.get("/{hosp_id}", response_model=HospitalizationResponse)
def get_hospitalization(
    hosp_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    hosp = db.query(Hospitalization).filter(Hospitalization.id == hosp_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")
    return _enrich_hospitalization(hosp, db)


@router.put("/{hosp_id}", response_model=HospitalizationResponse)
def update_hospitalization(
    hosp_id: int,
    data: HospitalizationUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    hosp = db.query(Hospitalization).filter(Hospitalization.id == hosp_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hosp, field, value)

    if data.status == HospitalizationStatus.DISCHARGED:
        hosp.discharged_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(hosp)
    return _enrich_hospitalization(hosp, db)


# --- Care Tasks ---
@router.post("/{hosp_id}/tasks", response_model=CareTaskResponse, status_code=201)
def add_care_task(
    hosp_id: int,
    data: CareTaskCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    hosp = db.query(Hospitalization).filter(Hospitalization.id == hosp_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")

    task = CareTask(hospitalization_id=hosp_id, **data.model_dump())
    if data.is_completed:
        task.is_completed = True
        task.completed_at = datetime.now(timezone.utc)
        task.completed_by_id = current_user.id
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{hosp_id}/tasks/{task_id}", response_model=CareTaskResponse)
def update_care_task(
    hosp_id: int,
    task_id: int,
    data: CareTaskUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(CareTask).filter(
        CareTask.id == task_id, CareTask.hospitalization_id == hosp_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")

    if data.is_completed is not None:
        task.is_completed = data.is_completed
        if data.is_completed:
            task.completed_at = datetime.now(timezone.utc)
            task.completed_by_id = current_user.id
    if data.notes is not None:
        task.notes = data.notes

    db.commit()
    db.refresh(task)
    return task
