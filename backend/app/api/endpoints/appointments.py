from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User, UserRole, Notification
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse, WaitingRoomUpdate,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    veterinarian_id: Optional[int] = Query(None),
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
    if status:
        query = query.filter(Appointment.status == status)
    return query.order_by(Appointment.start_time).offset(skip).limit(limit).all()


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
    return appointment


@router.get("/waiting-room", response_model=list[AppointmentResponse])
def get_waiting_room(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    return (
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
        .order_by(Appointment.start_time)
        .all()
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    return appt


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
    return appt


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
    return appt


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
