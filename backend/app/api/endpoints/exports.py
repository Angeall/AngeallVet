"""Excel exports: a generic stats export (the frontend posts the data it already
has) and a full tenant DB backup (server-side dump, admin only)."""

from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_tenant_db
from app.core.security import get_current_user, require_roles
from app.core.excel import build_workbook, workbook_response
from app.models.user import User, UserRole
from app.models import (
    Client, Animal, AnimalAlert, WeightRecord, Appointment, MedicalRecord,
    ConsultationTemplate, MedicalRecordProduct, Product, ProductLot, StockMovement,
    Supplier, PurchaseOrder, PurchaseOrderItem, Invoice, InvoiceLine,
    Estimate, EstimateLine, Payment, Communication, ReminderRule, Hospitalization,
    CareTask, ClinicSettings, VatRate, ControlledSubstanceEntry, Association,
    BillingRule, BillingRuleComponent, BillingProgram, BillingProgramDay, BillingDayOverride,
)
from app.models.billing import InvoiceVeterinarian
from app.models.client import ClientAlert, ClientNote
from app.models.animal import SpeciesRecord

router = APIRouter(prefix="/export", tags=["Export"])


# Tables included in the backup, in a human-readable order. (model, sheet title, excluded cols)
_BACKUP = [
    (Client, "Clients", []),
    (ClientAlert, "Alertes clients", []),
    (ClientNote, "Notes clients", []),
    (Animal, "Animaux", []),
    (AnimalAlert, "Alertes animaux", []),
    (WeightRecord, "Poids", []),
    (SpeciesRecord, "Especes", []),
    (Appointment, "Rendez-vous", []),
    (MedicalRecord, "Dossiers medicaux", []),
    (MedicalRecordProduct, "Produits dossiers", []),
    (ConsultationTemplate, "Templates SOAP", []),
    (Product, "Produits", []),
    (ProductLot, "Lots", []),
    (StockMovement, "Mouvements stock", []),
    (Supplier, "Fournisseurs", []),
    (PurchaseOrder, "Commandes", []),
    (PurchaseOrderItem, "Lignes commandes", []),
    (Invoice, "Factures", []),
    (InvoiceLine, "Lignes factures", []),
    (InvoiceVeterinarian, "Factures-veterinaires", []),
    (Payment, "Paiements", []),
    (Estimate, "Devis", []),
    (EstimateLine, "Lignes devis", []),
    (Hospitalization, "Hospitalisations", []),
    (CareTask, "Taches de soin", []),
    (ControlledSubstanceEntry, "Stupefiants", []),
    (Communication, "Communications", []),
    (ReminderRule, "Regles de rappel", []),
    (Association, "Associations", []),
    (VatRate, "Taux TVA", []),
    (ClinicSettings, "Cabinet", []),
    (BillingRule, "Regles facturation", []),
    (BillingRuleComponent, "Composants regles", []),
    (BillingProgram, "Programmes", []),
    (BillingProgramDay, "Jours programmes", []),
    (BillingDayOverride, "Overrides jour", []),
    (User, "Utilisateurs", ["google_calendar_token"]),
]


class SheetIn(BaseModel):
    title: str
    headers: list[str] = []
    rows: list[list[Any]] = []


class XlsxIn(BaseModel):
    filename: str = "export.xlsx"
    sheets: list[SheetIn]


@router.post("/xlsx")
def export_xlsx(data: XlsxIn, current_user: User = Depends(get_current_user)):
    """Turn caller-provided sheets into an .xlsx download (used by stats pages)."""
    wb = build_workbook([s.model_dump() for s in data.sheets])
    name = data.filename if data.filename.endswith(".xlsx") else f"{data.filename}.xlsx"
    return workbook_response(wb, name)


@router.get("/backup")
def export_backup(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Full tenant data backup: one sheet per table, as a single .xlsx workbook."""
    sheets = []
    for model, title, exclude in _BACKUP:
        cols = [c.name for c in model.__table__.columns if c.name not in exclude]
        rows = [[getattr(obj, c) for c in cols] for obj in db.query(model).all()]
        sheets.append({"title": title, "headers": cols, "rows": rows})
    wb = build_workbook(sheets)
    return workbook_response(wb, "backup_angeallvet.xlsx")
