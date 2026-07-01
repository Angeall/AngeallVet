"""Cash register closing + accounting export (the ``accounting`` paid module).

Admin / accountant only, gated behind the module. A closing finalises a business
day (Z-report) and locks it; the export endpoints produce a readable journal
workbook and a FEC file.
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles, require_module
from app.core.licensing import MODULE_ACCOUNTING
from app.core.excel import build_workbook, workbook_response
from app.core.accounting_export import build_journal_sheets, build_fec, METHOD_LABELS
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.billing import Invoice, Payment
from app.models.accounting import CashRegisterClosing, CashMovement

router = APIRouter(prefix="/accounting", tags=["Accounting"])

_accountant = require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)
_module = require_module(MODULE_ACCOUNTING)
ZERO = Decimal("0")


def _d(x) -> Decimal:
    return Decimal(str(x)) if x is not None else ZERO


def is_day_closed(db: Session, day: date) -> bool:
    """Used by the billing endpoints to reject changes on a closed day."""
    return db.query(CashRegisterClosing).filter(CashRegisterClosing.business_date == day).first() is not None


# ─── schemas ─────────────────────────────────────────────────────────────────

class MovementIn(BaseModel):
    direction: str                       # in | out
    amount: Decimal
    reason: Optional[str] = None
    business_date: Optional[date] = None  # default: today


class CloseIn(BaseModel):
    business_date: Optional[date] = None  # default: today
    opening_amount: Decimal = Decimal("0")
    counted_amount: Decimal = Decimal("0")
    notes: Optional[str] = None


def _closing_dict(c: CashRegisterClosing) -> dict:
    return {
        "id": c.id,
        "business_date": c.business_date.isoformat(),
        "opening_amount": float(c.opening_amount or 0),
        "counted_amount": float(c.counted_amount or 0),
        "expected_amount": float(c.expected_amount or 0),
        "discrepancy": float(c.discrepancy or 0),
        "total_amount": float(c.total_amount or 0),
        "payment_count": c.payment_count or 0,
        "totals_by_method": c.totals_by_method or {},
        "notes": c.notes,
        "closed_by_id": c.closed_by_id,
        "closed_at": c.closed_at.isoformat() if c.closed_at else None,
    }


def _day_figures(db: Session, day: date):
    payments = db.query(Payment).filter(Payment.payment_date == day).all()
    by_method, total = {}, ZERO
    for p in payments:
        m = p.payment_method or "other"
        by_method[m] = round(by_method.get(m, 0.0) + float(p.amount or 0), 2)
        total += _d(p.amount)
    movements = db.query(CashMovement).filter(CashMovement.business_date == day).all()
    cash_in = sum(float(m.amount or 0) for m in movements if m.direction == "in")
    cash_out = sum(float(m.amount or 0) for m in movements if m.direction == "out")
    return payments, by_method, float(total), movements, cash_in, cash_out


# ─── cash register ───────────────────────────────────────────────────────────

@router.get("/cash/day")
def cash_day(
    day: Optional[date] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    """The day's takings + cash movements, for the closing screen."""
    d = day or date.today()
    payments, by_method, total, movements, cash_in, cash_out = _day_figures(db, d)
    closing = db.query(CashRegisterClosing).filter(CashRegisterClosing.business_date == d).first()
    cash_payments = by_method.get("cash", 0.0)
    return {
        "date": d.isoformat(),
        "totals_by_method": by_method,
        "method_labels": METHOD_LABELS,
        "total": total,
        "payment_count": len(payments),
        "cash_payments": round(cash_payments, 2),
        "cash_in": round(cash_in, 2),
        "cash_out": round(cash_out, 2),
        # expected cash, excluding the opening fund (entered at closing time)
        "cash_movement_net": round(cash_payments + cash_in - cash_out, 2),
        "movements": [
            {"id": m.id, "direction": m.direction, "amount": float(m.amount or 0), "reason": m.reason}
            for m in movements
        ],
        "closed": bool(closing),
        "closing": _closing_dict(closing) if closing else None,
    }


@router.post("/cash/movements", status_code=201)
def add_movement(
    data: MovementIn,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    d = data.business_date or date.today()
    if is_day_closed(db, d):
        raise HTTPException(status_code=409, detail="Journée clôturée : mouvement impossible.")
    if data.direction not in ("in", "out"):
        raise HTTPException(status_code=400, detail="Sens invalide (in/out)")
    mv = CashMovement(
        business_date=d, direction=data.direction, amount=data.amount,
        reason=data.reason, created_by_id=current_user.id,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return {"id": mv.id, "direction": mv.direction, "amount": float(mv.amount), "reason": mv.reason}


@router.post("/cash/close")
def close_day(
    data: CloseIn,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    d = data.business_date or date.today()
    if is_day_closed(db, d):
        raise HTTPException(status_code=409, detail="Journée déjà clôturée.")
    payments, by_method, total, _movements, cash_in, cash_out = _day_figures(db, d)
    cash_payments = _d(by_method.get("cash", 0.0))
    expected = _d(data.opening_amount) + cash_payments + _d(cash_in) - _d(cash_out)
    counted = _d(data.counted_amount)
    closing = CashRegisterClosing(
        business_date=d,
        opening_amount=_d(data.opening_amount),
        counted_amount=counted,
        expected_amount=expected,
        discrepancy=counted - expected,
        total_amount=_d(total),
        payment_count=len(payments),
        totals_by_method=by_method,
        notes=data.notes,
        closed_by_id=current_user.id,
    )
    db.add(closing)
    db.commit()
    db.refresh(closing)
    return _closing_dict(closing)


@router.get("/cash/closings")
def list_closings(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    q = db.query(CashRegisterClosing)
    if date_from:
        q = q.filter(CashRegisterClosing.business_date >= date_from)
    if date_to:
        q = q.filter(CashRegisterClosing.business_date <= date_to)
    rows = q.order_by(CashRegisterClosing.business_date.desc()).limit(400).all()
    return [_closing_dict(c) for c in rows]


# ─── accounting export ───────────────────────────────────────────────────────

def _period_data(db: Session, date_from: date, date_to: date):
    invoices = (
        db.query(Invoice).options(selectinload(Invoice.lines))
        .filter(Invoice.issue_date >= date_from, Invoice.issue_date <= date_to).all()
    )
    payments = db.query(Payment).filter(
        Payment.payment_date >= date_from, Payment.payment_date <= date_to
    ).all()
    # Resolve pieces/clients for payments settling out-of-period invoices.
    inv_map = {inv.id: inv for inv in invoices}
    missing = {p.invoice_id for p in payments} - set(inv_map)
    if missing:
        for inv in db.query(Invoice).filter(Invoice.id.in_(missing)).all():
            inv_map[inv.id] = inv
    client_ids = {inv.client_id for inv in inv_map.values() if inv.client_id}
    client_names = {
        c.id: f"{c.first_name} {c.last_name}".strip()
        for c in (db.query(Client).filter(Client.id.in_(client_ids)).all() if client_ids else [])
    }
    return invoices, payments, client_names, inv_map


@router.get("/export/journal")
def export_journal(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    invoices, payments, client_names, inv_map = _period_data(db, date_from, date_to)
    sheets = build_journal_sheets(invoices, payments, client_names, inv_map=inv_map)
    wb = build_workbook(sheets)
    return workbook_response(wb, f"journal_comptable_{date_from}_{date_to}.xlsx")


@router.get("/export/fec")
def export_fec(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(_accountant),
    _m: bool = Depends(_module),
):
    invoices, payments, client_names, inv_map = _period_data(db, date_from, date_to)
    content = build_fec(invoices, payments, client_names, inv_map=inv_map)
    fname = f"FEC_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.txt"
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
