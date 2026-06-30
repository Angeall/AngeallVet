"""Invoice / quote document output.

By default every clinic gets a **simple PDF** rendered locally (free tier, see
``app.core.invoice_pdf``). The premium ``invoice_ninja`` module swaps invoice
output for Invoice Ninja's compliant PDF + Peppol e-invoicing: the push endpoint
is gated behind the module, and ``/invoices/{id}/pdf`` proxies Invoice Ninja only
when the module is active and the invoice was already pushed — otherwise it falls
back to the free local PDF.
"""

import io
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_module, tenant_has_module
from app.core.licensing import MODULE_INVOICE_NINJA
from app.core.invoice_ninja import (
    InvoiceNinjaClient, InvoiceNinjaError, client_payload, invoice_payload,
)
from app.core.invoice_pdf import render_invoice_pdf, render_estimate_pdf
from app.models.user import User
from app.models.client import Client
from app.models.billing import Invoice, Estimate
from app.models.settings import ClinicSettings

router = APIRouter(prefix="/billing", tags=["Invoice Ninja"])


def _client_for_tenant(db: Session) -> InvoiceNinjaClient:
    settings = db.query(ClinicSettings).first()
    if not settings or not settings.invoice_ninja_url or not settings.invoice_ninja_token:
        raise HTTPException(status_code=400, detail="Invoice Ninja non configuré (URL + token dans Paramètres)")
    return InvoiceNinjaClient(settings.invoice_ninja_url, settings.invoice_ninja_token)


def _pdf_response(pdf: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}.pdf"'},
    )


@router.post("/invoices/{invoice_id}/send")
def send_invoice_to_invoice_ninja(
    invoice_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_INVOICE_NINJA)),
):
    inj = _client_for_tenant(db)
    invoice = (
        db.query(Invoice).options(selectinload(Invoice.lines))
        .filter(Invoice.id == invoice_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    client = db.query(Client).filter(Client.id == invoice.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    try:
        # Commit ids step by step so a retry after a partial failure never
        # re-creates the client / invoice in Invoice Ninja.
        if not client.invoice_ninja_client_id:
            client.invoice_ninja_client_id = inj.create_client(client_payload(client))
            db.commit()
        if not invoice.invoice_ninja_invoice_id:
            created = inj.create_invoice(
                invoice_payload(client.invoice_ninja_client_id, invoice, list(invoice.lines))
            )
            invoice.invoice_ninja_invoice_id = created["id"]
            db.commit()
        inj.email_invoice(invoice.invoice_ninja_invoice_id)
    except InvoiceNinjaError as exc:
        raise HTTPException(status_code=502, detail=f"Invoice Ninja: {exc}")

    # A client with a VAT number is routed as a B2B Peppol e-invoice by Invoice
    # Ninja; otherwise the PDF is emailed (B2C).
    return {
        "ok": True,
        "invoice_ninja_invoice_id": invoice.invoice_ninja_invoice_id,
        "channel": "peppol" if client.vat_number else "email",
    }


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice).options(selectinload(Invoice.lines))
        .filter(Invoice.id == invoice_id).first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")

    # Premium path: Invoice Ninja's compliant PDF — only when the module is
    # active AND the invoice was already pushed there.
    if tenant_has_module(request, MODULE_INVOICE_NINJA) and invoice.invoice_ninja_invoice_id:
        clinic = db.query(ClinicSettings).first()
        if clinic and clinic.invoice_ninja_url and clinic.invoice_ninja_token:
            inj = InvoiceNinjaClient(clinic.invoice_ninja_url, clinic.invoice_ninja_token)
            try:
                pdf = inj.download_pdf(invoice.invoice_ninja_invoice_id)
            except InvoiceNinjaError as exc:
                raise HTTPException(status_code=502, detail=f"Invoice Ninja: {exc}")
            return _pdf_response(pdf, invoice.invoice_number)

    # Free default: locally rendered simple PDF.
    client = db.query(Client).filter(Client.id == invoice.client_id).first()
    clinic = db.query(ClinicSettings).first()
    pdf = render_invoice_pdf(invoice, list(invoice.lines), client, clinic)
    return _pdf_response(pdf, invoice.invoice_number)


@router.get("/estimates/{estimate_id}/pdf")
def estimate_pdf(
    estimate_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Free local PDF for a quote (devis) — available to every clinic."""
    estimate = (
        db.query(Estimate).options(selectinload(Estimate.lines))
        .filter(Estimate.id == estimate_id).first()
    )
    if not estimate:
        raise HTTPException(status_code=404, detail="Devis non trouvé")
    client = db.query(Client).filter(Client.id == estimate.client_id).first()
    clinic = db.query(ClinicSettings).first()
    pdf = render_estimate_pdf(estimate, list(estimate.lines), client, clinic)
    return _pdf_response(pdf, estimate.estimate_number)
