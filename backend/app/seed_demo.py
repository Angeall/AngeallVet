"""
Demo data seeder for AngeallVet.
Run: python -m app.seed_demo
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.animal import Animal, AnimalAlert, WeightRecord, Species, Sex
from app.models.appointment import Appointment, AppointmentType, AppointmentStatus
from app.models.medical import MedicalRecord, ConsultationTemplate, Prescription, PrescriptionItem, RecordType
from app.models.inventory import Product, ProductLot, Supplier, ProductType
from app.models.billing import Invoice, InvoiceLine, Estimate, EstimateLine, InvoiceStatus
from app.models.communication import ReminderRule
from app.models.hospitalization import Hospitalization, CareTask


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already contains data. Skipping seed.")
            return

        print("Seeding demo data...")

        # ==================== USERS ====================
        admin = User(
            email="admin@angeallvet.fr", hashed_password=hash_password("admin123"),
            first_name="Sophie", last_name="Martin", role=UserRole.ADMIN, phone="0601020304",
        )
        vet1 = User(
            email="dr.dupont@angeallvet.fr", hashed_password=hash_password("vet123"),
            first_name="Pierre", last_name="Dupont", role=UserRole.VETERINARIAN, phone="0605060708",
        )
        vet2 = User(
            email="dr.bernard@angeallvet.fr", hashed_password=hash_password("vet123"),
            first_name="Marie", last_name="Bernard", role=UserRole.VETERINARIAN, phone="0609101112",
        )
        asv = User(
            email="asv@angeallvet.fr", hashed_password=hash_password("asv123"),
            first_name="Julie", last_name="Petit", role=UserRole.ASSISTANT, phone="0613141516",
        )
        accountant = User(
            email="compta@angeallvet.fr", hashed_password=hash_password("compta123"),
            first_name="Marc", last_name="Lecomte", role=UserRole.ACCOUNTANT,
        )
        db.add_all([admin, vet1, vet2, asv, accountant])
        db.flush()

        # ==================== CLIENTS ====================
        clients_data = [
            {"first_name": "Jean", "last_name": "Moreau", "email": "jean.moreau@email.fr", "phone": "0145678901", "mobile": "0678901234", "address": "12 Rue de la Paix", "city": "Paris", "postal_code": "75001"},
            {"first_name": "Marie", "last_name": "Lefèvre", "email": "marie.lefevre@email.fr", "mobile": "0612345678", "address": "5 Avenue Victor Hugo", "city": "Lyon", "postal_code": "69002"},
            {"first_name": "Philippe", "last_name": "Garcia", "email": "p.garcia@email.fr", "mobile": "0698765432", "address": "8 Rue du Château", "city": "Bordeaux", "postal_code": "33000"},
            {"first_name": "Isabelle", "last_name": "Roux", "email": "isabelle.roux@email.fr", "mobile": "0654321098", "address": "22 Boulevard Pasteur", "city": "Toulouse", "postal_code": "31000"},
            {"first_name": "Laurent", "last_name": "Fournier", "email": "l.fournier@email.fr", "mobile": "0687654321", "address": "3 Place de la République", "city": "Marseille", "postal_code": "13001"},
        ]
        clients = []
        for cd in clients_data:
            c = Client(**cd)
            db.add(c)
            clients.append(c)
        db.flush()

        # ==================== ANIMALS ====================
        animals_data = [
            {"client": clients[0], "name": "Rex", "species": Species.DOG, "breed": "Berger Allemand", "sex": Sex.MALE, "dob": date(2019, 3, 15), "chip": "250269812345001", "neutered": False, "color": "Noir et feu"},
            {"client": clients[0], "name": "Bella", "species": Species.CAT, "breed": "Européen", "sex": Sex.FEMALE, "dob": date(2020, 7, 22), "chip": "250269812345002", "neutered": True, "color": "Tigrée"},
            {"client": clients[1], "name": "Luna", "species": Species.DOG, "breed": "Golden Retriever", "sex": Sex.FEMALE, "dob": date(2018, 1, 10), "chip": "250269812345003", "neutered": True, "color": "Doré"},
            {"client": clients[1], "name": "Simba", "species": Species.CAT, "breed": "Persan", "sex": Sex.MALE, "dob": date(2021, 5, 5), "chip": "250269812345004", "neutered": True, "color": "Roux"},
            {"client": clients[2], "name": "Max", "species": Species.DOG, "breed": "Labrador", "sex": Sex.MALE, "dob": date(2015, 9, 30), "chip": "250269812345005", "neutered": True, "color": "Chocolat"},
            {"client": clients[2], "name": "Coco", "species": Species.BIRD, "breed": "Perroquet Gris", "sex": Sex.UNKNOWN, "dob": date(2017, 2, 14), "chip": None, "neutered": False, "color": "Gris"},
            {"client": clients[3], "name": "Rocky", "species": Species.DOG, "breed": "Bouledogue Français", "sex": Sex.MALE, "dob": date(2022, 11, 1), "chip": "250269812345006", "neutered": False, "color": "Bringé"},
            {"client": clients[4], "name": "Nala", "species": Species.CAT, "breed": "Siamois", "sex": Sex.FEMALE, "dob": date(2023, 4, 18), "chip": "250269812345007", "neutered": False, "color": "Seal point"},
        ]
        animals = []
        for ad in animals_data:
            a = Animal(
                client_id=ad["client"].id, name=ad["name"], species=ad["species"],
                breed=ad["breed"], sex=ad["sex"], date_of_birth=ad["dob"],
                microchip_number=ad["chip"], is_neutered=ad["neutered"], color=ad["color"],
            )
            db.add(a)
            animals.append(a)
        db.flush()

        # ==================== ALERTS ====================
        db.add(AnimalAlert(animal_id=animals[0].id, alert_type="aggressive", message="Muselière obligatoire - A mordu un ASV en 2023", severity="danger"))
        db.add(AnimalAlert(animal_id=animals[2].id, alert_type="allergy", message="Allergique à la Pénicilline", severity="warning"))
        db.add(AnimalAlert(animal_id=animals[4].id, alert_type="chronic_disease", message="Arthrose sévère - Traitement AINS quotidien", severity="info"))

        # ==================== WEIGHT RECORDS ====================
        now = datetime.now(timezone.utc)
        for i, w in enumerate([28.5, 29.0, 29.5, 30.0, 30.2, 29.8]):
            db.add(WeightRecord(animal_id=animals[0].id, weight_kg=Decimal(str(w)), recorded_at=now - timedelta(days=180 - i * 30)))
        for i, w in enumerate([3.8, 4.0, 4.1, 4.2, 4.3]):
            db.add(WeightRecord(animal_id=animals[1].id, weight_kg=Decimal(str(w)), recorded_at=now - timedelta(days=150 - i * 30)))
        for i, w in enumerate([32.0, 33.0, 34.5, 35.0, 34.0, 33.5]):
            db.add(WeightRecord(animal_id=animals[4].id, weight_kg=Decimal(str(w)), recorded_at=now - timedelta(days=180 - i * 30)))

        # ==================== APPOINTMENTS ====================
        today = date.today()
        appts = [
            Appointment(client_id=clients[0].id, animal_id=animals[0].id, veterinarian_id=vet1.id,
                        appointment_type=AppointmentType.CONSULTATION, status=AppointmentStatus.CONFIRMED,
                        start_time=datetime.combine(today, datetime.min.time().replace(hour=9)),
                        end_time=datetime.combine(today, datetime.min.time().replace(hour=9, minute=30)),
                        reason="Boiterie patte arrière droite"),
            Appointment(client_id=clients[1].id, animal_id=animals[2].id, veterinarian_id=vet1.id,
                        appointment_type=AppointmentType.VACCINATION, status=AppointmentStatus.ARRIVED,
                        start_time=datetime.combine(today, datetime.min.time().replace(hour=10)),
                        end_time=datetime.combine(today, datetime.min.time().replace(hour=10, minute=15)),
                        reason="Rappel vaccin annuel"),
            Appointment(client_id=clients[2].id, animal_id=animals[4].id, veterinarian_id=vet2.id,
                        appointment_type=AppointmentType.CHECKUP, status=AppointmentStatus.SCHEDULED,
                        start_time=datetime.combine(today, datetime.min.time().replace(hour=11)),
                        end_time=datetime.combine(today, datetime.min.time().replace(hour=11, minute=30)),
                        reason="Contrôle arthrose trimestriel"),
            Appointment(client_id=clients[3].id, animal_id=animals[6].id, veterinarian_id=vet2.id,
                        appointment_type=AppointmentType.SURGERY, status=AppointmentStatus.SCHEDULED,
                        start_time=datetime.combine(today, datetime.min.time().replace(hour=14)),
                        end_time=datetime.combine(today, datetime.min.time().replace(hour=16)),
                        reason="Castration", color_code="#dc2626"),
        ]
        db.add_all(appts)
        db.flush()

        # ==================== CONSULTATION TEMPLATES ====================
        templates = [
            ConsultationTemplate(name="Vaccin annuel chien", category="vaccination", species="dog",
                                 subjective="Rappel vaccin annuel",
                                 objective="T: 38.5°C, FC: 100/min, FR: 20/min. Examen clinique normal. Muqueuses roses.",
                                 assessment="Animal en bonne santé. Apte à la vaccination.",
                                 plan="Injection CHPPiL + Rage SC. Rappel dans 12 mois. Carnet de vaccination mis à jour.",
                                 created_by_id=vet1.id),
            ConsultationTemplate(name="Vaccin annuel chat", category="vaccination", species="cat",
                                 subjective="Rappel vaccin annuel",
                                 objective="T: 38.5°C, FC: 180/min, FR: 25/min. Examen clinique normal.",
                                 assessment="Animal en bonne santé. Apte à la vaccination.",
                                 plan="Injection Typhus-Coryza-Leucose SC. Rappel dans 12 mois.",
                                 created_by_id=vet1.id),
            ConsultationTemplate(name="Gastro-entérite", category="consultation", species=None,
                                 subjective="Vomissements et/ou diarrhée depuis __ jours. Appétit diminué.",
                                 objective="T: __°C. Déshydratation __ %. Abdomen sensible à la palpation.",
                                 assessment="Gastro-entérite aiguë",
                                 plan="Diète 24h puis réalimentation progressive. Anti-émétique. Pansement digestif. Contrôle à J+3 si pas d'amélioration.",
                                 created_by_id=vet1.id),
            ConsultationTemplate(name="Détartrage", category="surgery", species=None,
                                 subjective="Tartre important, halitose",
                                 objective="Tartre grade __/4. Gingivite. Mobilité dentaire: __",
                                 assessment="Maladie parodontale grade __",
                                 plan="Détartrage sous AG. Extraction dentaire si nécessaire. ATB post-op si extractions.",
                                 created_by_id=vet2.id),
        ]
        db.add_all(templates)
        db.flush()

        # ==================== MEDICAL RECORDS ====================
        rec1 = MedicalRecord(
            animal_id=animals[0].id, veterinarian_id=vet1.id, record_type=RecordType.VACCINATION,
            subjective="Rappel vaccin annuel", objective="Examen clinique normal. T: 38.4°C",
            assessment="Apte à la vaccination", plan="CHPPiL + Rage. Rappel mars 2027.",
            created_at=now - timedelta(days=365),
        )
        rec2 = MedicalRecord(
            animal_id=animals[0].id, veterinarian_id=vet1.id, record_type=RecordType.CONSULTATION,
            subjective="Boiterie patte arrière gauche depuis 3 jours",
            objective="Douleur à la manipulation du grasset. Test du tiroir positif.",
            assessment="Suspicion de rupture du ligament croisé antérieur",
            plan="Radio sous sédation. Si confirmé: chirurgie TPLO recommandée.",
            created_at=now - timedelta(days=90),
        )
        rec3 = MedicalRecord(
            animal_id=animals[2].id, veterinarian_id=vet2.id, record_type=RecordType.CONSULTATION,
            subjective="Grattage intense depuis 1 semaine, zones rouges",
            objective="Érythème face ventrale, interdigité. Pas de parasites visibles.",
            assessment="Dermatite allergique - suspicion atopie",
            plan="Cytoponctions cutanées. Régime d'éviction 8 semaines. Apoquel 16mg/j.",
            created_at=now - timedelta(days=60),
        )
        db.add_all([rec1, rec2, rec3])
        db.flush()

        # Add prescription to rec3
        presc = Prescription(medical_record_id=rec3.id, notes="À réévaluer dans 2 semaines")
        db.add(presc)
        db.flush()
        db.add(PrescriptionItem(
            prescription_id=presc.id, medication_name="Apoquel (oclacitinib)",
            dosage="16mg", dosage_per_kg=Decimal("0.5"), frequency="1x/jour",
            duration="14 jours", quantity=Decimal("14"),
        ))

        # ==================== SUPPLIERS ====================
        supplier1 = Supplier(name="Centravet", contact_name="Service commercial", email="commandes@centravet.fr", phone="0800123456")
        supplier2 = Supplier(name="Alcyon", contact_name="Jean Commandes", email="commandes@alcyon.fr", phone="0800654321")
        db.add_all([supplier1, supplier2])
        db.flush()

        # ==================== PRODUCTS ====================
        products_data = [
            {"name": "Consultation", "type": ProductType.SERVICE, "price": Decimal("45.00"), "vat": Decimal("20.00"), "unit": "acte", "supplier": None},
            {"name": "Vaccination CHPPiL", "type": ProductType.MEDICATION, "price": Decimal("35.00"), "vat": Decimal("20.00"), "unit": "dose", "supplier": supplier1},
            {"name": "Vaccin Rage", "type": ProductType.MEDICATION, "price": Decimal("25.00"), "vat": Decimal("20.00"), "unit": "dose", "supplier": supplier1},
            {"name": "Amoxicilline 250mg", "type": ProductType.MEDICATION, "price": Decimal("0.80"), "vat": Decimal("20.00"), "unit": "comprimé", "supplier": supplier1},
            {"name": "Apoquel 16mg", "type": ProductType.MEDICATION, "price": Decimal("3.50"), "vat": Decimal("20.00"), "unit": "comprimé", "supplier": supplier2},
            {"name": "Metacam 1.5mg/ml", "type": ProductType.MEDICATION, "price": Decimal("22.00"), "vat": Decimal("20.00"), "unit": "flacon", "supplier": supplier1},
            {"name": "Royal Canin Gastro", "type": ProductType.FOOD, "price": Decimal("35.00"), "vat": Decimal("5.50"), "unit": "sac 2kg", "supplier": supplier2},
            {"name": "Hill's z/d", "type": ProductType.FOOD, "price": Decimal("42.00"), "vat": Decimal("5.50"), "unit": "sac 3kg", "supplier": supplier2},
            {"name": "Castration chien <10kg", "type": ProductType.SERVICE, "price": Decimal("180.00"), "vat": Decimal("20.00"), "unit": "acte", "supplier": None},
            {"name": "Détartrage", "type": ProductType.SERVICE, "price": Decimal("120.00"), "vat": Decimal("20.00"), "unit": "acte", "supplier": None},
        ]
        products = []
        for i, pd in enumerate(products_data):
            p = Product(
                name=pd["name"], reference=f"PRD-{i+1:04d}",
                product_type=pd["type"], selling_price=pd["price"],
                vat_rate=pd["vat"], unit=pd["unit"],
                supplier_id=pd["supplier"].id if pd["supplier"] else None,
                stock_quantity=Decimal("0") if pd["type"] == ProductType.SERVICE else Decimal("50"),
                stock_alert_threshold=Decimal("0") if pd["type"] == ProductType.SERVICE else Decimal("10"),
            )
            db.add(p)
            products.append(p)
        db.flush()

        # Add lots for medications
        for p in products:
            if p.product_type == ProductType.MEDICATION:
                db.add(ProductLot(
                    product_id=p.id, lot_number=f"LOT-2025-{p.id:03d}",
                    expiry_date=date(2026, 12, 31), quantity=Decimal("50"),
                ))
                # Add a lot expiring soon for demo
                if p.name == "Amoxicilline 250mg":
                    db.add(ProductLot(
                        product_id=p.id, lot_number=f"LOT-2024-{p.id:03d}",
                        expiry_date=date.today() + timedelta(days=15), quantity=Decimal("10"),
                    ))

        # ==================== INVOICES ====================
        inv1 = Invoice(
            invoice_number="FAC-2025-0001", client_id=clients[0].id, animal_id=animals[0].id,
            status=InvoiceStatus.PAID, subtotal=Decimal("80.00"), total_vat=Decimal("16.00"),
            total=Decimal("96.00"), amount_paid=Decimal("96.00"), created_by_id=vet1.id,
        )
        db.add(inv1)
        db.flush()
        db.add(InvoiceLine(invoice_id=inv1.id, description="Consultation", quantity=Decimal("1"), unit_price=Decimal("45.00"), vat_rate=Decimal("20.00"), line_total=Decimal("45.00")))
        db.add(InvoiceLine(invoice_id=inv1.id, description="Vaccination CHPPiL", quantity=Decimal("1"), unit_price=Decimal("35.00"), vat_rate=Decimal("20.00"), line_total=Decimal("35.00")))

        inv2 = Invoice(
            invoice_number="FAC-2025-0002", client_id=clients[2].id, animal_id=animals[4].id,
            status=InvoiceStatus.SENT, subtotal=Decimal("67.00"), total_vat=Decimal("13.40"),
            total=Decimal("80.40"), amount_paid=Decimal("0"), created_by_id=vet2.id,
            due_date=date.today() - timedelta(days=15),
        )
        db.add(inv2)
        db.flush()
        db.add(InvoiceLine(invoice_id=inv2.id, description="Consultation", quantity=Decimal("1"), unit_price=Decimal("45.00"), vat_rate=Decimal("20.00"), line_total=Decimal("45.00")))
        db.add(InvoiceLine(invoice_id=inv2.id, description="Metacam 1.5mg/ml", quantity=Decimal("1"), unit_price=Decimal("22.00"), vat_rate=Decimal("20.00"), line_total=Decimal("22.00")))

        # ==================== ESTIMATES ====================
        est1 = Estimate(
            estimate_number="DEV-2025-0001", client_id=clients[3].id, animal_id=animals[6].id,
            status="sent", subtotal=Decimal("180.00"), total_vat=Decimal("36.00"), total=Decimal("216.00"),
            valid_until=date.today() + timedelta(days=30), created_by_id=vet2.id,
        )
        db.add(est1)
        db.flush()
        db.add(EstimateLine(estimate_id=est1.id, description="Castration chien <10kg", quantity=Decimal("1"), unit_price=Decimal("180.00"), vat_rate=Decimal("20.00"), line_total=Decimal("180.00")))

        # ==================== REMINDER RULES ====================
        db.add(ReminderRule(
            name="Rappel vaccin annuel", reminder_type="vaccine", channel="email",
            days_before=30, days_before_second=7, days_after=1,
            email_template="Bonjour {client_name}, le vaccin de {animal_name} arrive à échéance le {due_date}. Prenez RDV au 01 23 45 67 89.",
        ))
        db.add(ReminderRule(
            name="Rappel antiparasitaire", reminder_type="antiparasitic", channel="sms",
            days_before=7, days_before_second=1, days_after=0,
            sms_template="AngeallVet: Le traitement antiparasitaire de {animal_name} arrive à échéance. Contactez-nous.",
        ))

        # ==================== HOSPITALIZATION ====================
        hosp = Hospitalization(
            animal_id=animals[4].id, veterinarian_id=vet2.id,
            reason="Post-opératoire chirurgie TPLO genou droit",
            cage_number="C3",
        )
        db.add(hosp)
        db.flush()

        care_tasks_data = [
            {"hour": 8, "type": "medication", "desc": "Morphine 0.3mg/kg IM"},
            {"hour": 8, "type": "vitals", "desc": "Prise de température + FC + FR"},
            {"hour": 12, "type": "medication", "desc": "Metacam 0.1mg/kg SC"},
            {"hour": 12, "type": "feeding", "desc": "Proposer eau + alimentation légère"},
            {"hour": 14, "type": "observation", "desc": "Vérifier pansement, état de la plaie"},
            {"hour": 18, "type": "vitals", "desc": "Prise de température + FC + FR"},
            {"hour": 20, "type": "medication", "desc": "Morphine 0.3mg/kg IM"},
            {"hour": 22, "type": "observation", "desc": "Vérification dernière ronde"},
        ]
        for ct in care_tasks_data:
            db.add(CareTask(
                hospitalization_id=hosp.id,
                scheduled_at=datetime.combine(today, datetime.min.time().replace(hour=ct["hour"])),
                task_type=ct["type"],
                description=ct["desc"],
            ))

        db.commit()
        print("Demo data seeded successfully!")
        print("\nComptes de démonstration:")
        print("  Admin:        admin@angeallvet.fr / admin123")
        print("  Vétérinaire:  dr.dupont@angeallvet.fr / vet123")
        print("  ASV:          asv@angeallvet.fr / asv123")
        print("  Comptable:    compta@angeallvet.fr / compta123")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
