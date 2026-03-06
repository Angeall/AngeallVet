from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.hospitalization import Hospitalization, CareTask, HospitalizationStatus
from app.schemas.hospitalization import (
    HospitalizationCreate, HospitalizationUpdate, HospitalizationResponse,
    CareTaskCreate, CareTaskUpdate, CareTaskResponse,
)

router = APIRouter(prefix="/hospitalization", tags=["Hospitalization"])


@router.get("", response_model=list[HospitalizationResponse])
def list_hospitalizations(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Hospitalization)
    if active_only:
        query = query.filter(Hospitalization.status == HospitalizationStatus.ACTIVE)
    return query.order_by(Hospitalization.admitted_at.desc()).all()


@router.post("", response_model=HospitalizationResponse, status_code=201)
def create_hospitalization(
    data: HospitalizationCreate,
    db: Session = Depends(get_db),
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
    return hosp


@router.get("/{hosp_id}", response_model=HospitalizationResponse)
def get_hospitalization(
    hosp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hosp = db.query(Hospitalization).filter(Hospitalization.id == hosp_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")
    return hosp


@router.put("/{hosp_id}", response_model=HospitalizationResponse)
def update_hospitalization(
    hosp_id: int,
    data: HospitalizationUpdate,
    db: Session = Depends(get_db),
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
    return hosp


# --- Care Tasks ---
@router.post("/{hosp_id}/tasks", response_model=CareTaskResponse, status_code=201)
def add_care_task(
    hosp_id: int,
    data: CareTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hosp = db.query(Hospitalization).filter(Hospitalization.id == hosp_id).first()
    if not hosp:
        raise HTTPException(status_code=404, detail="Hospitalisation non trouvée")

    task = CareTask(hospitalization_id=hosp_id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{hosp_id}/tasks/{task_id}", response_model=CareTaskResponse)
def update_care_task(
    hosp_id: int,
    task_id: int,
    data: CareTaskUpdate,
    db: Session = Depends(get_db),
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
