from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime, Date,
    ForeignKey, Enum as SAEnum, Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class RecordType(str, enum.Enum):
    CONSULTATION = "consultation"
    VACCINATION = "vaccination"
    SURGERY = "surgery"
    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    NOTE = "note"


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=False, index=True)
    veterinarian_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True, index=True)
    record_type = Column(SAEnum(RecordType), nullable=False, index=True)
    # SOAP format
    subjective = Column(Text)  # Motif / Anamnèse
    objective = Column(Text)   # Examen clinique
    assessment = Column(Text)  # Diagnostic
    plan = Column(Text)        # Plan de traitement
    home_treatment = Column(Text)  # Traitement à la maison
    pharmacy_prescription = Column(Text)  # Médicaments à aller chercher en pharmacie
    notes = Column(Text)
    template_id = Column(Integer, ForeignKey("consultation_templates.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    animal = relationship("Animal", back_populates="medical_records")
    prescriptions = relationship("Prescription", back_populates="medical_record")
    attachments = relationship("Attachment", back_populates="medical_record")
    home_treatment_products = relationship("MedicalRecordProduct", back_populates="medical_record")


class ConsultationTemplate(Base):
    __tablename__ = "consultation_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    species = Column(String(50))
    subjective = Column(Text)
    objective = Column(Text)
    assessment = Column(Text)
    plan = Column(Text)
    home_treatment = Column(Text)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("ConsultationTemplateProduct", back_populates="template", cascade="all, delete-orphan")


class ConsultationTemplateProduct(Base):
    __tablename__ = "consultation_template_products"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("consultation_templates.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Numeric(10, 2), default=1)
    treatment_location = Column(String(20), default="onsite")  # "onsite" or "home"

    template = relationship("ConsultationTemplate", back_populates="products")
    product = relationship("Product")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, index=True)
    prescription_date = Column(Date, server_default=func.current_date())
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")
    items = relationship("PrescriptionItem", back_populates="prescription")


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    medication_name = Column(String(200), nullable=False)
    dosage = Column(String(200))
    dosage_per_kg = Column(Numeric(10, 4))  # mg/kg for auto-calculation
    frequency = Column(String(100))
    duration = Column(String(100))
    quantity = Column(Numeric(10, 2))
    instructions = Column(Text)

    prescription = relationship("Prescription", back_populates="items")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))  # image, pdf, dicom
    file_size = Column(Integer)
    description = Column(String(500))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), index=True)

    medical_record = relationship("MedicalRecord", back_populates="attachments")


class MedicalRecordProduct(Base):
    __tablename__ = "medical_record_products"

    id = Column(Integer, primary_key=True, index=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Numeric(10, 2), default=1)
    treatment_location = Column(String(20), default="home")  # "home" or "onsite"
    lot_number = Column(String(100))

    medical_record = relationship("MedicalRecord", back_populates="home_treatment_products")
    product = relationship("Product")
