from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from typing import Optional
from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.billing import (
    Invoice, InvoiceLine, Estimate, EstimateLine, Payment, InvoiceStatus,
)
from app.models.client import Client
from app.models.inventory import Product, StockMovement
from app.models.settings import ClinicSettings
from app.schemas.billing import (
    InvoiceCreate, InvoiceUpdate, InvoiceResponse,
    EstimateCreate, EstimateResponse,
    PaymentCreate, PaymentResponse,
    EstimateToInvoiceRequest,
)

router = APIRouter(prefix="/billing", tags=["Billing & Invoicing"])


def _calculate_line_total(line) -> Decimal:
    subtotal = line.quantity * line.unit_price
    discount = subtotal * (line.discount_percent / 100) if hasattr(line, "discount_percent") and line.discount_percent else 0
    return subtotal - discount


def _calculate_invoice_totals(lines):
    subtotal = Decimal("0")
    total_vat = Decimal("0")
    for line in lines:
        lt = _calculate_line_total(line)
        subtotal += lt
        total_vat += lt * (line.vat_rate / 100)
    return subtotal, total_vat, subtotal + total_vat


def _enrich_invoice(inv, db):
    """Add client_name to an invoice."""
    from app.schemas.billing import InvoiceResponse as IR
    data = IR.model_validate(inv).model_dump()
    client = db.query(Client).filter(Client.id == inv.client_id).first()
    if client:
        data["client_name"] = f"{client.last_name} {client.first_name}"
    return data


# --- Invoices ---
@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if status:
        query = query.filter(Invoice.status == status)
    if date_from:
        query = query.filter(Invoice.issue_date >= date_from)
    if date_to:
        query = query.filter(Invoice.issue_date <= date_to)
    if search:
        # Search by invoice number or client name
        client_ids = db.query(Client.id).filter(
            (Client.last_name.ilike(f"%{search}%")) | (Client.first_name.ilike(f"%{search}%"))
        ).all()
        client_id_list = [c[0] for c in client_ids]
        query = query.filter(
            (Invoice.invoice_number.ilike(f"%{search}%")) | (Invoice.client_id.in_(client_id_list))
        )
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich_invoice(inv, db) for inv in invoices]


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    invoice_number = f"FAC-{uuid.uuid4().hex[:8].upper()}"
    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=data.client_id,
        animal_id=data.animal_id,
        due_date=data.due_date,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(invoice)
    db.flush()

    for line_data in data.lines:
        line = InvoiceLine(
            invoice_id=invoice.id,
            **line_data.model_dump(),
        )
        line.line_total = _calculate_line_total(line_data)
        db.add(line)

        # Auto destock if product
        if line_data.product_id:
            product = db.query(Product).filter(Product.id == line_data.product_id).first()
            if product and product.product_type != "service":
                product.stock_quantity = max(0, (product.stock_quantity or 0) - line_data.quantity)
                movement = StockMovement(
                    product_id=product.id,
                    movement_type="out",
                    quantity=line_data.quantity,
                    reason=f"Facture {invoice_number}",
                    reference_type="invoice",
                    reference_id=invoice.id,
                    performed_by_id=current_user.id,
                )
                db.add(movement)

    subtotal, total_vat, total = _calculate_invoice_totals(data.lines)
    invoice.subtotal = subtotal
    invoice.total_vat = total_vat
    invoice.total = total

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    return invoice


@router.get("/unpaid", response_model=list[InvoiceResponse])
def list_unpaid(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Invoice)
        .filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]))
        .order_by(Invoice.due_date)
        .all()
    )


# --- Payments ---
@router.post("/payments", response_model=PaymentResponse, status_code=201)
def record_payment(
    data: PaymentCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == data.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    payment = Payment(
        **data.model_dump(),
        received_by_id=current_user.id,
    )
    db.add(payment)

    invoice.amount_paid = (invoice.amount_paid or 0) + data.amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = InvoiceStatus.PAID
        # Update client balance
        client = db.query(Client).filter(Client.id == invoice.client_id).first()
        if client:
            client.account_balance = (client.account_balance or 0) + (invoice.amount_paid - invoice.total)
    else:
        invoice.status = InvoiceStatus.PARTIAL

    db.commit()
    db.refresh(payment)
    return payment


# --- Estimates ---
@router.post("/estimates", response_model=EstimateResponse, status_code=201)
def create_estimate(
    data: EstimateCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    estimate_number = f"DEV-{uuid.uuid4().hex[:8].upper()}"
    estimate = Estimate(
        estimate_number=estimate_number,
        client_id=data.client_id,
        animal_id=data.animal_id,
        valid_until=data.valid_until,
        notes=data.notes,
        created_by_id=current_user.id,
    )
    db.add(estimate)
    db.flush()

    for line_data in data.lines:
        line = EstimateLine(
            estimate_id=estimate.id,
            **line_data.model_dump(),
        )
        lt = line_data.quantity * line_data.unit_price
        line.line_total = lt
        db.add(line)

    subtotal = sum(l.quantity * l.unit_price for l in data.lines)
    total_vat = sum(l.quantity * l.unit_price * l.vat_rate / 100 for l in data.lines)
    estimate.subtotal = subtotal
    estimate.total_vat = total_vat
    estimate.total = subtotal + total_vat

    db.commit()
    db.refresh(estimate)
    return estimate


@router.get("/estimates", response_model=list[EstimateResponse])
def list_estimates(
    client_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Estimate)
    if client_id:
        query = query.filter(Estimate.client_id == client_id)
    return query.order_by(Estimate.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/estimates/{estimate_id}", response_model=EstimateResponse)
def get_estimate(
    estimate_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    estimate = db.query(Estimate).filter(Estimate.id == estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    return estimate


@router.post("/estimates/to-invoice", response_model=InvoiceResponse)
def convert_estimate_to_invoice(
    data: EstimateToInvoiceRequest,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    estimate = db.query(Estimate).filter(Estimate.id == data.estimate_id).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Devis non trouvé")

    invoice_number = f"FAC-{uuid.uuid4().hex[:8].upper()}"
    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=estimate.client_id,
        animal_id=estimate.animal_id,
        subtotal=estimate.subtotal,
        total_vat=estimate.total_vat,
        total=estimate.total,
        notes=estimate.notes,
        estimate_id=estimate.id,
        created_by_id=current_user.id,
    )
    db.add(invoice)
    db.flush()

    for el in estimate.lines:
        line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=el.product_id,
            description=el.description,
            quantity=el.quantity,
            unit_price=el.unit_price,
            vat_rate=el.vat_rate,
            line_total=el.line_total,
        )
        db.add(line)

    estimate.status = "invoiced"
    db.commit()
    db.refresh(invoice)
    return invoice


# ─── Debt Acknowledgment ─────────────────────────────────────────────

@router.get("/invoices/{invoice_id}/debt-acknowledgment")
def get_debt_acknowledgment(
    invoice_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Return data needed to generate a debt acknowledgment document."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    remaining = float(invoice.total or 0) - float(invoice.amount_paid or 0)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Cette facture est déjà payée")

    client = db.query(Client).filter(Client.id == invoice.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    clinic = db.query(ClinicSettings).first()

    return {
        "clinic": {
            "clinic_name": clinic.clinic_name if clinic else None,
            "address": clinic.address if clinic else None,
            "city": clinic.city if clinic else None,
            "postal_code": clinic.postal_code if clinic else None,
            "phone": clinic.phone if clinic else None,
            "email": clinic.email if clinic else None,
            "siret": clinic.siret if clinic else None,
            "vat_number": clinic.vat_number if clinic else None,
        },
        "client": {
            "id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "address": client.address,
            "city": client.city,
            "postal_code": client.postal_code,
            "email": client.email,
            "phone": client.phone,
            "vat_number": client.vat_number,
        },
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "subtotal": round(float(invoice.subtotal or 0), 2),
            "total_vat": round(float(invoice.total_vat or 0), 2),
            "total": round(float(invoice.total or 0), 2),
            "amount_paid": round(float(invoice.amount_paid or 0), 2),
            "remaining": round(remaining, 2),
        },
        "lines": [
            {
                "description": line.description,
                "quantity": round(float(line.quantity or 1), 2),
                "unit_price": round(float(line.unit_price or 0), 2),
                "vat_rate": round(float(line.vat_rate or 0), 2),
                "discount_percent": round(float(line.discount_percent or 0), 2),
                "line_total": round(float(line.line_total or 0), 2),
            }
            for line in invoice.lines
        ],
        "template": clinic.debt_acknowledgment_template if clinic else None,
    }


# ─── Debts (clients with outstanding balances) ──────────────────────

@router.get("/debts")
def list_debts(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Return clients with unpaid invoices, sorted by outstanding amount DESC."""
    results = (
        db.query(
            Client.id,
            Client.first_name,
            Client.last_name,
            Client.email,
            Client.phone,
            sa_func.count(Invoice.id).label("invoice_count"),
            sa_func.coalesce(sa_func.sum(Invoice.total), 0).label("total_due"),
            sa_func.coalesce(sa_func.sum(Invoice.amount_paid), 0).label("total_paid"),
            (
                sa_func.coalesce(sa_func.sum(Invoice.total), 0)
                - sa_func.coalesce(sa_func.sum(Invoice.amount_paid), 0)
            ).label("outstanding"),
        )
        .join(Invoice, Invoice.client_id == Client.id)
        .filter(
            Invoice.status.in_([
                InvoiceStatus.SENT,
                InvoiceStatus.PARTIAL,
                InvoiceStatus.OVERDUE,
                InvoiceStatus.DRAFT,
            ])
        )
        .group_by(Client.id, Client.first_name, Client.last_name, Client.email, Client.phone)
        .having(
            sa_func.coalesce(sa_func.sum(Invoice.total), 0)
            - sa_func.coalesce(sa_func.sum(Invoice.amount_paid), 0)
            > 0
        )
        .order_by(sa_func.text("outstanding DESC"))
        .all()
    )

    return [
        {
            "client_id": r.id,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "email": r.email,
            "phone": r.phone,
            "invoice_count": r.invoice_count,
            "total_due": round(float(r.total_due), 2),
            "total_paid": round(float(r.total_paid), 2),
            "outstanding": round(float(r.outstanding), 2),
        }
        for r in results
    ]


# ─── Statistics ─────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    period: str = Query("day", description="day, week, month"),
    date_ref: Optional[date] = Query(None, description="Reference date"),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Return billing stats for a given period.

    Returns:
    - current period totals (revenue, paid, unpaid, count)
    - previous period totals for comparison
    - daily breakdown for chart
    """
    ref = date_ref or date.today()

    if period == "day":
        start = ref
        end = ref
        prev_start = ref - timedelta(days=1)
        prev_end = ref - timedelta(days=1)
    elif period == "week":
        start = ref - timedelta(days=ref.weekday())  # Monday
        end = start + timedelta(days=6)
        prev_start = start - timedelta(days=7)
        prev_end = end - timedelta(days=7)
    else:  # month
        start = ref.replace(day=1)
        if ref.month == 12:
            end = ref.replace(year=ref.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = ref.replace(month=ref.month + 1, day=1) - timedelta(days=1)
        prev_start = (start - timedelta(days=1)).replace(day=1)
        prev_end = start - timedelta(days=1)

    def _period_stats(d_start, d_end):
        invoices = db.query(Invoice).filter(
            Invoice.issue_date >= d_start,
            Invoice.issue_date <= d_end,
        ).all()

        total_revenue = sum(float(inv.total or 0) for inv in invoices)
        total_paid = sum(float(inv.amount_paid or 0) for inv in invoices)
        total_unpaid = total_revenue - total_paid
        count = len(invoices)
        paid_count = sum(1 for inv in invoices if inv.status == InvoiceStatus.PAID)

        # Breakdown by status
        by_status = {}
        for inv in invoices:
            s = inv.status.value if hasattr(inv.status, 'value') else str(inv.status)
            by_status[s] = by_status.get(s, 0) + float(inv.total or 0)

        return {
            "total_revenue": round(total_revenue, 2),
            "total_paid": round(total_paid, 2),
            "total_unpaid": round(total_unpaid, 2),
            "invoice_count": count,
            "paid_count": paid_count,
            "by_status": by_status,
        }

    current_stats = _period_stats(start, end)
    previous_stats = _period_stats(prev_start, prev_end)

    # Daily breakdown for chart
    daily = []
    day_cursor = start
    while day_cursor <= end:
        day_invoices = db.query(Invoice).filter(
            Invoice.issue_date == day_cursor,
        ).all()
        day_revenue = sum(float(inv.total or 0) for inv in day_invoices)
        day_paid = sum(float(inv.amount_paid or 0) for inv in day_invoices)
        daily.append({
            "date": day_cursor.isoformat(),
            "revenue": round(day_revenue, 2),
            "paid": round(day_paid, 2),
            "count": len(day_invoices),
        })
        day_cursor += timedelta(days=1)

    # Payment methods breakdown
    payments = db.query(Payment).filter(
        Payment.payment_date >= start,
        Payment.payment_date <= end,
    ).all()
    by_payment_method = {}
    for p in payments:
        method = p.payment_method or "other"
        by_payment_method[method] = round(
            by_payment_method.get(method, 0) + float(p.amount or 0), 2
        )

    return {
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "current": current_stats,
        "previous": previous_stats,
        "daily": daily,
        "by_payment_method": by_payment_method,
    }
