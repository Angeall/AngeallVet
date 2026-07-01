"""Vaccination protocols + administrations (the ``vaccine_protocols`` module).

Admins configure protocols; vets record administrations and the engine schedules
the next dose/booster (``next_due_date``), which feeds the "due" list and the
automated reminders.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles, require_module
from app.core.licensing import MODULE_VACCINE_PROTOCOLS
from app.models.user import User, UserRole
from app.models.animal import Animal
from app.models.client import Client
from app.models.vaccination import VaccineProtocol, VaccineProtocolDose, Vaccination

router = APIRouter(prefix="/vaccinations", tags=["Vaccinations"])

_module = require_module(MODULE_VACCINE_PROTOCOLS)
_admin = require_roles(UserRole.ADMIN)


# ─── next-due engine ─────────────────────────────────────────────────────────

def compute_next_due(protocol: VaccineProtocol, dose: VaccineProtocolDose, administered: date):
    """(next_due_date, next_label) for the dose just given, or (None, None)."""
    if not protocol or not dose:
        return None, None
    doses = sorted(protocol.doses, key=lambda x: (x.sequence, x.id))
    idx = next((i for i, x in enumerate(doses) if x.id == dose.id), None)
    if idx is None:
        return None, None
    if idx + 1 < len(doses):
        nxt = doses[idx + 1]
        return administered + timedelta(days=nxt.interval_days or 0), (nxt.label or nxt.valence)
    if dose.is_booster and dose.booster_interval_days:
        return administered + timedelta(days=dose.booster_interval_days), f"Rappel {dose.valence or dose.label}"
    return None, None


# ─── schemas ─────────────────────────────────────────────────────────────────

class DoseIn(BaseModel):
    sequence: int = 0
    label: str
    valence: Optional[str] = None
    interval_days: int = 0
    is_booster: bool = False
    booster_interval_days: Optional[int] = None


class DoseOut(DoseIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProtocolIn(BaseModel):
    name: str
    species: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    doses: list[DoseIn] = []


class ProtocolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    species: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    doses: list[DoseOut] = []


class VaccinationIn(BaseModel):
    animal_id: int
    protocol_id: Optional[int] = None
    dose_id: Optional[int] = None
    valence: Optional[str] = None
    date_administered: date
    lot_number: Optional[str] = None
    notes: Optional[str] = None
    next_due_date: Optional[date] = None  # manual override when no protocol/dose


# ─── protocols (admin) ───────────────────────────────────────────────────────

@router.get("/protocols", response_model=list[ProtocolOut])
def list_protocols(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _m: bool = Depends(_module),
):
    return (
        db.query(VaccineProtocol).options(selectinload(VaccineProtocol.doses))
        .order_by(VaccineProtocol.name).all()
    )


@router.post("/protocols", response_model=ProtocolOut, status_code=201)
def create_protocol(
    data: ProtocolIn,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
    _m: bool = Depends(_module),
):
    proto = VaccineProtocol(name=data.name, species=data.species, description=data.description, is_active=data.is_active)
    db.add(proto)
    db.flush()
    for d in data.doses:
        db.add(VaccineProtocolDose(protocol_id=proto.id, **d.model_dump()))
    db.commit()
    db.refresh(proto)
    return proto


@router.put("/protocols/{protocol_id}", response_model=ProtocolOut)
def update_protocol(
    protocol_id: int,
    data: ProtocolIn,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
    _m: bool = Depends(_module),
):
    proto = db.query(VaccineProtocol).filter(VaccineProtocol.id == protocol_id).first()
    if not proto:
        raise HTTPException(status_code=404, detail="Protocole introuvable")
    proto.name, proto.species, proto.description, proto.is_active = data.name, data.species, data.description, data.is_active
    db.query(VaccineProtocolDose).filter(VaccineProtocolDose.protocol_id == protocol_id).delete()
    for d in data.doses:
        db.add(VaccineProtocolDose(protocol_id=protocol_id, **d.model_dump()))
    db.commit()
    db.refresh(proto)
    return proto


@router.delete("/protocols/{protocol_id}", status_code=204)
def delete_protocol(
    protocol_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_admin),
    _m: bool = Depends(_module),
):
    proto = db.query(VaccineProtocol).filter(VaccineProtocol.id == protocol_id).first()
    if not proto:
        raise HTTPException(status_code=404, detail="Protocole introuvable")
    proto.is_active = False
    db.commit()


# ─── administrations ─────────────────────────────────────────────────────────

def _vax_dict(v: Vaccination) -> dict:
    return {
        "id": v.id, "animal_id": v.animal_id, "protocol_id": v.protocol_id, "dose_id": v.dose_id,
        "valence": v.valence, "date_administered": v.date_administered.isoformat() if v.date_administered else None,
        "lot_number": v.lot_number, "notes": v.notes,
        "next_due_date": v.next_due_date.isoformat() if v.next_due_date else None,
        "next_label": v.next_label,
    }


@router.post("", status_code=201)
def record_vaccination(
    data: VaccinationIn,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _m: bool = Depends(_module),
):
    if not db.query(Animal).filter(Animal.id == data.animal_id).first():
        raise HTTPException(status_code=404, detail="Animal introuvable")

    next_due, next_label = data.next_due_date, None
    valence = data.valence
    if data.protocol_id and data.dose_id:
        proto = (
            db.query(VaccineProtocol).options(selectinload(VaccineProtocol.doses))
            .filter(VaccineProtocol.id == data.protocol_id).first()
        )
        dose = next((d for d in proto.doses if d.id == data.dose_id), None) if proto else None
        if not dose:
            raise HTTPException(status_code=400, detail="Dose du protocole introuvable")
        valence = valence or dose.valence
        next_due, next_label = compute_next_due(proto, dose, data.date_administered)

    if not valence:
        raise HTTPException(status_code=400, detail="Valence requise")

    vax = Vaccination(
        animal_id=data.animal_id, protocol_id=data.protocol_id, dose_id=data.dose_id,
        valence=valence, date_administered=data.date_administered, lot_number=data.lot_number,
        notes=data.notes, veterinarian_id=current_user.id,
        next_due_date=next_due, next_label=next_label,
    )
    db.add(vax)
    db.commit()
    db.refresh(vax)
    return _vax_dict(vax)


@router.get("")
def list_for_animal(
    animal_id: int = Query(...),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _m: bool = Depends(_module),
):
    rows = (
        db.query(Vaccination).filter(Vaccination.animal_id == animal_id)
        .order_by(Vaccination.date_administered.desc(), Vaccination.id.desc()).all()
    )
    vet_ids = {v.veterinarian_id for v in rows if v.veterinarian_id}
    vets = {u.id: u for u in db.query(User).filter(User.id.in_(vet_ids)).all()} if vet_ids else {}
    out = []
    for v in rows:
        vet = vets.get(v.veterinarian_id)
        out.append({**_vax_dict(v), "veterinarian_name": f"{vet.first_name} {vet.last_name}".strip() if vet else None})
    return out


@router.get("/due")
def due_list(
    within_days: int = Query(30, description="Include reminders due within N days (and any overdue)"),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _m: bool = Depends(_module),
):
    """Active next-dose schedules due soon or overdue, one per (animal, valence)."""
    cutoff = date.today() + timedelta(days=within_days)
    rows = (
        db.query(Vaccination)
        .filter(Vaccination.next_due_date.isnot(None))
        .order_by(Vaccination.date_administered.desc(), Vaccination.id.desc())
        .limit(5000).all()
    )
    # Keep only the latest administration per (animal, valence) — the live schedule.
    latest = {}
    for v in rows:
        latest.setdefault((v.animal_id, (v.valence or "").lower()), v)
    due = [v for v in latest.values() if v.next_due_date and v.next_due_date <= cutoff]

    animal_ids = {v.animal_id for v in due}
    animals = {a.id: a for a in db.query(Animal).filter(Animal.id.in_(animal_ids)).all()} if animal_ids else {}
    client_ids = {a.client_id for a in animals.values()}
    clients = {c.id: c for c in db.query(Client).filter(Client.id.in_(client_ids)).all()} if client_ids else {}

    today = date.today()
    out = []
    for v in sorted(due, key=lambda x: x.next_due_date):
        a = animals.get(v.animal_id)
        c = clients.get(a.client_id) if a else None
        out.append({
            **_vax_dict(v),
            "animal_name": a.name if a else None,
            "species": a.species if a else None,
            "client_id": a.client_id if a else None,
            "client_name": f"{c.first_name} {c.last_name}".strip() if c else None,
            "overdue": v.next_due_date < today,
        })
    return out
