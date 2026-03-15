from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.settings import ClinicSettings, VatRate
from app.schemas.settings import (
    ClinicSettingsUpdate, ClinicSettingsResponse,
    VatRateCreate, VatRateUpdate, VatRateResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# ────────────────────── Clinic Settings ──────────────────────


@router.get("/clinic", response_model=ClinicSettingsResponse)
def get_clinic_settings(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(ClinicSettings).first()
    if not settings:
        settings = ClinicSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("/clinic", response_model=ClinicSettingsResponse)
def update_clinic_settings(
    data: ClinicSettingsUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    settings = db.query(ClinicSettings).first()
    if not settings:
        settings = ClinicSettings()
        db.add(settings)
        db.flush()

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


# ────────────────────── VAT Rates ──────────────────────


@router.get("/vat-rates", response_model=list[VatRateResponse])
def list_vat_rates(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(VatRate).filter(VatRate.is_active == True).order_by(VatRate.rate).all()


@router.post("/vat-rates", response_model=VatRateResponse, status_code=201)
def create_vat_rate(
    data: VatRateCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    if data.is_default:
        db.query(VatRate).filter(VatRate.is_default == True).update({"is_default": False})

    rate = VatRate(**data.model_dump())
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.put("/vat-rates/{rate_id}", response_model=VatRateResponse)
def update_vat_rate(
    rate_id: int,
    data: VatRateUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    rate = db.query(VatRate).filter(VatRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Taux de TVA introuvable")

    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("is_default"):
        db.query(VatRate).filter(VatRate.id != rate_id, VatRate.is_default == True).update({"is_default": False})

    for field, value in update_data.items():
        setattr(rate, field, value)

    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/vat-rates/{rate_id}", status_code=204)
def delete_vat_rate(
    rate_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    rate = db.query(VatRate).filter(VatRate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Taux de TVA introuvable")
    rate.is_active = False
    db.commit()
