"""Veterinarian commission engine: rules, weekly programs, day overrides, and the
per-vet commission report. Admin-only (it drives how much each vet is paid)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from datetime import date

from app.api.deps import get_tenant_db
from app.core.security import require_roles
from app.core.commissions import compute_commissions
from app.models.user import User, UserRole
from app.models.billing_rules import (
    BillingRule, BillingRuleComponent, BillingProgram, BillingProgramDay,
    BillingDayOverride,
)
from app.schemas.billing_rules import (
    RuleCreate, RuleResponse, ProgramCreate, ProgramResponse,
    VetProgramAssign, DayOverrideRequest,
)

router = APIRouter(prefix="/billing", tags=["Billing Rules"])

_admin = require_roles(UserRole.ADMIN)


# ── Rules ────────────────────────────────────────────────────────────
@router.get("/rules", response_model=list[RuleResponse])
def list_rules(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    return (
        db.query(BillingRule)
        .options(selectinload(BillingRule.components))
        .order_by(BillingRule.name)
        .all()
    )


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(
    data: RuleCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    rule = BillingRule(name=data.name, description=data.description, is_active=data.is_active)
    db.add(rule)
    db.flush()
    for c in data.components:
        db.add(BillingRuleComponent(rule_id=rule.id, **c.model_dump()))
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    data: RuleCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    rule = db.query(BillingRule).filter(BillingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    rule.name = data.name
    rule.description = data.description
    rule.is_active = data.is_active
    db.query(BillingRuleComponent).filter(BillingRuleComponent.rule_id == rule_id).delete()
    for c in data.components:
        db.add(BillingRuleComponent(rule_id=rule_id, **c.model_dump()))
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    rule = db.query(BillingRule).filter(BillingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    # Soft-deactivate: a rule may still be referenced by programs / past overrides.
    rule.is_active = False
    db.commit()


# ── Programs ─────────────────────────────────────────────────────────
@router.get("/programs", response_model=list[ProgramResponse])
def list_programs(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    return (
        db.query(BillingProgram)
        .options(selectinload(BillingProgram.days))
        .order_by(BillingProgram.name)
        .all()
    )


@router.post("/programs", response_model=ProgramResponse, status_code=201)
def create_program(
    data: ProgramCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    program = BillingProgram(name=data.name, is_active=data.is_active)
    db.add(program)
    db.flush()
    for d in data.days:
        db.add(BillingProgramDay(program_id=program.id, weekday=d.weekday, rule_id=d.rule_id))
    db.commit()
    db.refresh(program)
    return program


@router.put("/programs/{program_id}", response_model=ProgramResponse)
def update_program(
    program_id: int,
    data: ProgramCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    program = db.query(BillingProgram).filter(BillingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Programme non trouvé")
    program.name = data.name
    program.is_active = data.is_active
    db.query(BillingProgramDay).filter(BillingProgramDay.program_id == program_id).delete()
    for d in data.days:
        db.add(BillingProgramDay(program_id=program_id, weekday=d.weekday, rule_id=d.rule_id))
    db.commit()
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}", status_code=204)
def delete_program(
    program_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    program = db.query(BillingProgram).filter(BillingProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Programme non trouvé")
    program.is_active = False
    db.commit()


# ── Vet assignment ───────────────────────────────────────────────────
@router.get("/veterinarians")
def list_billing_vets(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    vets = (
        db.query(User)
        .filter(User.role.in_([UserRole.VETERINARIAN, UserRole.ADMIN]), User.is_active == True)
        .order_by(User.last_name, User.first_name)
        .all()
    )
    return [
        {"id": u.id, "name": f"{u.first_name} {u.last_name}", "billing_program_id": u.billing_program_id}
        for u in vets
    ]


@router.put("/veterinarians/{user_id}/program")
def assign_program(
    user_id: int,
    data: VetProgramAssign,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    user.billing_program_id = data.program_id
    db.commit()
    return {"ok": True}


# ── Commission report + day override ─────────────────────────────────
@router.get("/commissions")
def commissions_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    veterinarian_id: Optional[int] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    return compute_commissions(db, date_from, date_to, veterinarian_id)


@router.put("/commissions/day-rule")
def set_day_rule(
    data: DayOverrideRequest,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
):
    existing = (
        db.query(BillingDayOverride)
        .filter(BillingDayOverride.user_id == data.user_id, BillingDayOverride.date == data.date)
        .first()
    )
    if data.rule_id is None:
        if existing:
            db.delete(existing)
            db.commit()
        return {"ok": True, "cleared": True}
    if existing:
        existing.rule_id = data.rule_id
    else:
        db.add(BillingDayOverride(user_id=data.user_id, date=data.date, rule_id=data.rule_id))
    db.commit()
    return {"ok": True}
