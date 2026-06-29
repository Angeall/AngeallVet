from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from datetime import datetime, timezone

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.core.idempotency import (
    idempotency_key_header, replayed_entity_id, remember_entity,
)
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


def _enrich_hospitalizations(hosps, db):
    """Batch version of _enrich_hospitalization (care_tasks eager-loaded; animal/
    client/vet/task-user names resolved in a few queries for the whole page)."""
    if not hosps:
        return []
    datas = [HospitalizationResponse.model_validate(h).model_dump() for h in hosps]
    animal_ids = {h.animal_id for h in hosps if h.animal_id}
    animals = {a.id: a for a in db.query(Animal).filter(Animal.id.in_(animal_ids))} if animal_ids else {}
    client_ids = {a.client_id for a in animals.values() if a.client_id}
    clients = {c.id: c for c in db.query(Client).filter(Client.id.in_(client_ids))} if client_ids else {}
    user_ids = {h.veterinarian_id for h in hosps if h.veterinarian_id}
    user_ids |= {
        t["completed_by_id"]
        for d in datas
        for t in d.get("care_tasks", [])
        if t.get("completed_by_id")
    }
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids))} if user_ids else {}
    for h, data in zip(hosps, datas):
        animal = animals.get(h.animal_id)
        if animal:
            data["animal_name"] = animal.name
            data["client_id"] = animal.client_id
            client = clients.get(animal.client_id)
            if client:
                data["client_name"] = f"{client.last_name} {client.first_name}"
        vet = users.get(h.veterinarian_id)
        if vet:
            data["veterinarian_name"] = f"Dr. {vet.last_name}"
        for task in data.get("care_tasks", []):
            u = users.get(task.get("completed_by_id"))
            if u:
                task["completed_by_name"] = f"{u.first_name} {u.last_name}"
    return datas


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
    hosps = (
        query.options(selectinload(Hospitalization.care_tasks))
        .order_by(Hospitalization.admitted_at.desc())
        .all()
    )
    return _enrich_hospitalizations(hosps, db)


@router.post("", response_model=HospitalizationResponse, status_code=201)
def create_hospitalization(
    data: HospitalizationCreate,
    idem_key: Optional[str] = Depends(idempotency_key_header),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    prior_id = replayed_entity_id(db, idem_key, "hospitalization")
    if prior_id is not None:
        existing = db.query(Hospitalization).filter(Hospitalization.id == prior_id).first()
        if existing:
            return _enrich_hospitalization(existing, db)
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

    remember_entity(db, idem_key, "hospitalization", hosp.id)
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
