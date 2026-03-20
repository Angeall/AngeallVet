from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User, UserRole, Notification
from app.models.appointment import Appointment, AppointmentStatus
from app.models.animal import Animal
from app.models.client import Client
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse, WaitingRoomUpdate,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _enrich_appointment(appt, db):
    """Add veterinarian_name, client_name, animal_name to appointment."""
    vet = db.query(User).filter(User.id == appt.veterinarian_id).first() if appt.veterinarian_id else None
    appt.veterinarian_name = f"Dr. {vet.last_name} {vet.first_name}" if vet else None
    client = db.query(Client).filter(Client.id == appt.client_id).first() if appt.client_id else None
    appt.client_name = f"{client.last_name} {client.first_name}" if client else None
    animal = db.query(Animal).filter(Animal.id == appt.animal_id).first() if appt.animal_id else None
    appt.animal_name = animal.name if animal else None
    return appt


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    veterinarian_id: Optional[int] = Query(None),
    animal_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Appointment)
    if date_from:
        query = query.filter(Appointment.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Appointment.start_time <= datetime.combine(date_to, datetime.max.time()))
    if veterinarian_id:
        query = query.filter(Appointment.veterinarian_id == veterinarian_id)
    if animal_id:
        query = query.filter(Appointment.animal_id == animal_id)
    if status:
        query = query.filter(Appointment.status == status)
    appointments = query.order_by(Appointment.start_time).offset(skip).limit(limit).all()
    return [_enrich_appointment(a, db) for a in appointments]


@router.post("", response_model=AppointmentResponse, status_code=201)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appointment = Appointment(**data.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return _enrich_appointment(appointment, db)


@router.get("/waiting-room", response_model=list[AppointmentResponse])
def get_waiting_room(
    veterinarian_id: Optional[int] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    query = (
        db.query(Appointment)
        .filter(
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time <= datetime.combine(today, datetime.max.time()),
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.ARRIVED,
                AppointmentStatus.IN_PROGRESS,
            ]),
        )
    )
    if veterinarian_id:
        query = query.filter(Appointment.veterinarian_id == veterinarian_id)
    appointments = query.order_by(Appointment.start_time).all()
    return [_enrich_appointment(a, db) for a in appointments]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    return _enrich_appointment(appt, db)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)

    db.commit()
    db.refresh(appt)
    return _enrich_appointment(appt, db)


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_waiting_room_status(
    appointment_id: int,
    data: WaitingRoomUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")

    old_status = appt.status
    appt.status = data.status

    # Notify veterinarian(s) when a client arrives in the waiting room
    if data.status in (AppointmentStatus.ARRIVED, "arrived"):
        vet_ids = set()
        # Notify the assigned vet
        if appt.veterinarian_id:
            vet_ids.add(appt.veterinarian_id)
        # Also notify all vets if no specific vet is assigned
        if not vet_ids:
            vets = db.query(User).filter(
                User.role == UserRole.VETERINARIAN,
                User.is_active == True,
            ).all()
            vet_ids = {v.id for v in vets}

        time_str = appt.start_time.strftime("%H:%M") if appt.start_time else ""
        reason = appt.reason or appt.appointment_type.value if appt.appointment_type else "RDV"
        for vet_id in vet_ids:
            notif = Notification(
                user_id=vet_id,
                title="Patient en salle d'attente",
                message=f"RDV {time_str} - {reason}",
                notification_type="waiting_room",
                link="/waiting-room",
            )
            db.add(notif)

    db.commit()
    db.refresh(appt)
    return _enrich_appointment(appt, db)


@router.delete("/{appointment_id}", status_code=204)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    appt.status = AppointmentStatus.CANCELLED
    db.commit()
