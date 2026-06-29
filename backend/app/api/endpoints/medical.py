import os
import uuid as uuid_mod
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from decimal import Decimal

from app.api.deps import get_tenant_db
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.core.tenancy import tenant_from_request
from app.models.user import User, UserRole
from app.models.medical import (
    MedicalRecord, ConsultationTemplate, ConsultationTemplateProduct, Prescription,
    PrescriptionItem, Attachment, MedicalRecordProduct,
)
from app.models.animal import Animal, WeightRecord
from app.models.inventory import Product
from app.models.billing import Invoice, InvoiceLine, InvoiceStatus, InvoiceVeterinarian
from app.schemas.medical import (
    MedicalRecordCreate, MedicalRecordResponse,
    ConsultationTemplateCreate, ConsultationTemplateResponse,
    AttachmentResponse,
)
from app.schemas.billing import InvoiceResponse

router = APIRouter(prefix="/medical", tags=["Medical Records"])


def _enrich_record(record, db):
    """Add product_name, veterinarian_name, and invoice_id."""
    data = MedicalRecordResponse.model_validate(record).model_dump()
    for p in data.get("home_treatment_products", []):
        product = db.query(Product).filter(Product.id == p["product_id"]).first()
        if product:
            p["product_name"] = product.name
    # Veterinarian name
    vet = db.query(User).filter(User.id == record.veterinarian_id).first()
    if vet:
        data["veterinarian_name"] = f"Dr. {vet.last_name}"
    # Check if an invoice was created from this record
    invoice = db.query(Invoice).filter(Invoice.medical_record_id == record.id).first()
    if invoice:
        data["invoice_id"] = invoice.id
    return data


def _enrich_records(records, db):
    """Batch version of _enrich_record: with relationships eager-loaded, resolves
    vet names, source invoices and home-treatment product names in 3 queries for
    the whole page (instead of several per record)."""
    if not records:
        return []
    datas = [MedicalRecordResponse.model_validate(r).model_dump() for r in records]
    vet_ids = {r.veterinarian_id for r in records if r.veterinarian_id}
    vets = {u.id: u for u in db.query(User).filter(User.id.in_(vet_ids))} if vet_ids else {}
    rec_ids = [r.id for r in records]
    inv_map = {}
    if rec_ids:
        for inv_id, mr_id in db.query(Invoice.id, Invoice.medical_record_id).filter(
            Invoice.medical_record_id.in_(rec_ids)
        ):
            inv_map[mr_id] = inv_id
    prod_ids = {
        p["product_id"]
        for d in datas
        for p in d.get("home_treatment_products", [])
        if p.get("product_id")
    }
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(prod_ids))} if prod_ids else {}
    for r, data in zip(records, datas):
        for p in data.get("home_treatment_products", []):
            prod = products.get(p.get("product_id"))
            if prod:
                p["product_name"] = prod.name
        vet = vets.get(r.veterinarian_id)
        if vet:
            data["veterinarian_name"] = f"Dr. {vet.last_name}"
        if r.id in inv_map:
            data["invoice_id"] = inv_map[r.id]
    return datas


@router.get("/records", response_model=list[MedicalRecordResponse])
def list_records(
    animal_id: Optional[int] = Query(None),
    record_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(MedicalRecord)
    if animal_id:
        query = query.filter(MedicalRecord.animal_id == animal_id)
    if record_type:
        query = query.filter(MedicalRecord.record_type == record_type)
    records = (
        query.options(
            selectinload(MedicalRecord.prescriptions).selectinload(Prescription.items),
            selectinload(MedicalRecord.attachments),
            selectinload(MedicalRecord.home_treatment_products),
        )
        .order_by(MedicalRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return _enrich_records(records, db)


@router.post("/records", response_model=MedicalRecordResponse, status_code=201)
def create_record(
    data: MedicalRecordCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    record_data = data.model_dump(exclude={"prescriptions", "weight_kg", "home_treatment_products", "onsite_treatment_products"})
    record = MedicalRecord(**record_data, veterinarian_id=current_user.id)
    db.add(record)
    db.flush()

    for presc_data in data.prescriptions:
        presc = Prescription(
            medical_record_id=record.id,
            notes=presc_data.notes,
        )
        db.add(presc)
        db.flush()
        for item_data in presc_data.items:
            item = PrescriptionItem(
                prescription_id=presc.id,
                **item_data.model_dump(),
            )
            db.add(item)

    # Record weight if provided
    if data.weight_kg is not None:
        weight_record = WeightRecord(
            animal_id=data.animal_id,
            weight_kg=data.weight_kg,
            recorded_by_id=current_user.id,
        )
        db.add(weight_record)

    # Save home treatment products
    for htp in data.home_treatment_products:
        mrp = MedicalRecordProduct(
            medical_record_id=record.id,
            product_id=htp.product_id,
            quantity=htp.quantity,
            treatment_location="home",
            lot_number=htp.lot_number,
        )
        db.add(mrp)

    # Save on-site treatment products
    for otp in data.onsite_treatment_products:
        mrp = MedicalRecordProduct(
            medical_record_id=record.id,
            product_id=otp.product_id,
            quantity=otp.quantity,
            treatment_location="onsite",
            lot_number=otp.lot_number,
        )
        db.add(mrp)

    db.commit()
    db.refresh(record)
    return _enrich_record(record, db)


@router.get("/records/{record_id}", response_model=MedicalRecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dossier medical non trouve")
    return _enrich_record(record, db)


@router.post("/records/{record_id}/create-invoice", response_model=InvoiceResponse, status_code=201)
def create_invoice_from_record(
    record_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dossier medical non trouve")

    # Check if an invoice already exists for this record
    existing_invoice = db.query(Invoice).filter(Invoice.medical_record_id == record_id).first()
    if existing_invoice:
        return existing_invoice

    if not record.home_treatment_products:
        raise HTTPException(status_code=400, detail="Aucun produit de traitement a domicile")

    animal = db.query(Animal).filter(Animal.id == record.animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal non trouve")

    invoice_number = f"FAC-{uuid_mod.uuid4().hex[:8].upper()}"
    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=animal.client_id,
        animal_id=animal.id,
        medical_record_id=record_id,
        created_by_id=current_user.id,
    )
    db.add(invoice)
    db.flush()

    subtotal = Decimal("0")
    total_vat = Decimal("0")

    for mrp in record.home_treatment_products:
        product = db.query(Product).filter(Product.id == mrp.product_id).first()
        if not product:
            continue
        unit_price = product.selling_price or Decimal("0")
        vat_rate = Decimal(str(product.vat_rate)) if product.vat_rate else Decimal("20")
        qty = mrp.quantity or Decimal("1")
        line_total = qty * unit_price

        line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=product.id,
            description=product.name,
            quantity=qty,
            unit_price=unit_price,
            vat_rate=vat_rate,
            line_total=line_total,
            lot_number=mrp.lot_number,
        )
        db.add(line)
        subtotal += line_total
        total_vat += line_total * (vat_rate / 100)

    invoice.subtotal = subtotal
    invoice.total_vat = total_vat
    invoice.total = subtotal + total_vat

    # Auto-add current user as veterinarian on the invoice
    db.add(InvoiceVeterinarian(invoice_id=invoice.id, user_id=current_user.id))

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/records/{record_id}/attachments", response_model=AttachmentResponse)
def upload_attachment(
    record_id: int,
    request: Request,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dossier medical non trouve")

    # Per-tenant storage so attachments are never shared across tenants.
    tenant = tenant_from_request(request)
    upload_dir = os.path.join(settings.UPLOAD_DIR, tenant.slug, "medical", str(record_id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_name = f"{uuid_mod.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, stored_name)

    # Read at most the allowed size (+1 byte) so an oversized upload can't
    # exhaust memory before the size check.
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux")

    with open(file_path, "wb") as f:
        f.write(content)

    file_type = "image" if ext.lower() in (".jpg", ".jpeg", ".png", ".gif") else "pdf" if ext.lower() == ".pdf" else "other"

    attachment = Attachment(
        medical_record_id=record_id,
        file_name=file.filename or stored_name,
        file_path=file_path,
        file_type=file_type,
        file_size=len(content),
        description=description,
        uploaded_by_id=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Stream a medical attachment to an authenticated user of this tenant.

    Files are served here (not via a public static mount) and forced as a
    download to prevent inline rendering / stored XSS. The attachment row lives
    in the tenant DB, so cross-tenant access is structurally impossible.
    """
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Piece jointe non trouvee")

    # Defense-in-depth: never serve a path outside the upload directory.
    base = os.path.realpath(settings.UPLOAD_DIR)
    real = os.path.realpath(att.file_path)
    if not (real == base or real.startswith(base + os.sep)) or not os.path.exists(real):
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    return FileResponse(
        real,
        filename=att.file_name,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )


# --- Templates ---
@router.get("/templates", response_model=list[ConsultationTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ConsultationTemplate).filter(ConsultationTemplate.is_active == True)
    if category:
        query = query.filter(ConsultationTemplate.category == category)
    if species:
        query = query.filter(ConsultationTemplate.species == species)
    return query.order_by(ConsultationTemplate.name).all()


@router.get("/templates/{template_id}", response_model=ConsultationTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(ConsultationTemplate).filter(ConsultationTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    return template


@router.post("/templates", response_model=ConsultationTemplateResponse, status_code=201)
def create_template(
    data: ConsultationTemplateCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    template_data = data.model_dump(exclude={"products"})
    template = ConsultationTemplate(**template_data, created_by_id=current_user.id)
    db.add(template)
    db.flush()

    for p in data.products:
        tp = ConsultationTemplateProduct(
            template_id=template.id,
            product_id=p.product_id,
            quantity=p.quantity,
            treatment_location=p.treatment_location,
        )
        db.add(tp)

    db.commit()
    db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=ConsultationTemplateResponse)
def update_template(
    template_id: int,
    data: ConsultationTemplateCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    template = db.query(ConsultationTemplate).filter(ConsultationTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template non trouvé")

    template_data = data.model_dump(exclude={"products"})
    for field, value in template_data.items():
        setattr(template, field, value)

    # Replace products
    db.query(ConsultationTemplateProduct).filter(
        ConsultationTemplateProduct.template_id == template_id
    ).delete()

    for p in data.products:
        tp = ConsultationTemplateProduct(
            template_id=template.id,
            product_id=p.product_id,
            quantity=p.quantity,
            treatment_location=p.treatment_location,
        )
        db.add(tp)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    template = db.query(ConsultationTemplate).filter(ConsultationTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    template.is_active = False
    db.commit()
