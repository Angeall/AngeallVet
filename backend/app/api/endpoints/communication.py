from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.communication import Communication, ReminderRule, ReminderLog
from app.schemas.communication import (
    CommunicationCreate, CommunicationResponse,
    ReminderRuleCreate, ReminderRuleResponse,
)

router = APIRouter(prefix="/communications", tags=["Communications & Reminders"])


@router.get("", response_model=list[CommunicationResponse])
def list_communications(
    client_id: Optional[int] = Query(None),
    channel: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Communication)
    if client_id:
        query = query.filter(Communication.client_id == client_id)
    if channel:
        query = query.filter(Communication.channel == channel)
    return query.order_by(Communication.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=CommunicationResponse, status_code=201)
def send_communication(
    data: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comm = Communication(**data.model_dump())
    # In production, this would actually send via SMTP/SMS provider
    comm.status = "sent"
    db.add(comm)
    db.commit()
    db.refresh(comm)
    return comm


# --- Reminder Rules ---
@router.get("/reminders", response_model=list[ReminderRuleResponse])
def list_reminder_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ReminderRule).order_by(ReminderRule.name).all()


@router.post("/reminders", response_model=ReminderRuleResponse, status_code=201)
def create_reminder_rule(
    data: ReminderRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = ReminderRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/reminders/{rule_id}", response_model=ReminderRuleResponse)
def update_reminder_rule(
    rule_id: int,
    data: ReminderRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(ReminderRule).filter(ReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")

    for field, value in data.model_dump().items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/reminders/{rule_id}", status_code=204)
def delete_reminder_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(ReminderRule).filter(ReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    rule.is_active = False
    db.commit()
