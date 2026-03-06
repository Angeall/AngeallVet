import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.medical import (
    MedicalRecord, ConsultationTemplate, Prescription,
    PrescriptionItem, Attachment,
)
from app.schemas.medical import (
    MedicalRecordCreate, MedicalRecordResponse,
    ConsultationTemplateCreate, ConsultationTemplateResponse,
    AttachmentResponse,
)

router = APIRouter(prefix="/medical", tags=["Medical Records"])


@router.get("/records", response_model=list[MedicalRecordResponse])
def list_records(
    animal_id: Optional[int] = Query(None),
    record_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(MedicalRecord)
    if animal_id:
        query = query.filter(MedicalRecord.animal_id == animal_id)
    if record_type:
        query = query.filter(MedicalRecord.record_type == record_type)
    return query.order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/records", response_model=MedicalRecordResponse, status_code=201)
def create_record(
    data: MedicalRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    record_data = data.model_dump(exclude={"prescriptions"})
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

    db.commit()
    db.refresh(record)
    return record


@router.get("/records/{record_id}", response_model=MedicalRecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dossier médical non trouvé")
    return record


@router.post("/records/{record_id}/attachments", response_model=AttachmentResponse)
def upload_attachment(
    record_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dossier médical non trouvé")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "medical", str(record_id))
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, stored_name)

    content = file.file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
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


# --- Templates ---
@router.get("/templates", response_model=list[ConsultationTemplateResponse])
def list_templates(
    category: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ConsultationTemplate).filter(ConsultationTemplate.is_active == True)
    if category:
        query = query.filter(ConsultationTemplate.category == category)
    if species:
        query = query.filter(ConsultationTemplate.species == species)
    return query.order_by(ConsultationTemplate.name).all()


@router.post("/templates", response_model=ConsultationTemplateResponse, status_code=201)
def create_template(
    data: ConsultationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VETERINARIAN)),
):
    template = ConsultationTemplate(**data.model_dump(), created_by_id=current_user.id)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
