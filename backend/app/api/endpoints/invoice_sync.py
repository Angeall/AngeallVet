"""Push AngeallVet invoices to the clinic's Invoice Ninja instance (PDF + Peppol).

Invoice Ninja owns the compliant output; here we sync the client + invoice and
trigger the send. The created Invoice Ninja ids are stored back on our rows so a
resend never creates duplicates.
"""

import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.core.invoice_ninja import (
    InvoiceNinjaClient, InvoiceNinjaError, client_payload, invoice_payload,
)
from app.models.user import User
from app.models.client import Client
from app.models.billing import Invoice
from app.models.settings import ClinicSettings

router = APIRouter(prefix="/billing", tags=["Invoice Ninja"])


def _client_for_tenant(db: Session) -> InvoiceNinjaClient:
    settings = db.query(ClinicSettings).first()
    if not settings or not settings.invoice_ninja_url or not settings.invoice_ninja_token:
        raise HTTPException(status_code=400, detail="Invoice Ninja non configuré (URL + token dans Paramètres)")
    return InvoiceNinjaClient(settings.invoice_ninja_url, settings.invoice_ninja_token)


@router.post("/invoices/{invoice_id}/send")
def send_invoice_to_invoice_ninja(
    invoice_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
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
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    if not invoice.invoice_ninja_invoice_id:
        raise HTTPException(status_code=400, detail="Facture pas encore envoyée à Invoice Ninja")
    inj = _client_for_tenant(db)
    try:
        pdf = inj.download_pdf(invoice.invoice_ninja_invoice_id)
    except InvoiceNinjaError as exc:
        raise HTTPException(status_code=502, detail=f"Invoice Ninja: {exc}")
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'},
    )
