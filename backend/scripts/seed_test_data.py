"""
Seed script: generates realistic test data for AngeallVet over ~1 year.

Usage:
    cd backend
    python -m scripts.seed_test_data

WARNING: This script inserts data directly into the database configured in .env.
         It is intended for development/testing only.
"""

import os
import sys
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.animal import Animal, AnimalAlert, WeightRecord, SpeciesRecord
from app.models.appointment import Appointment, AppointmentType, AppointmentStatus
from app.models.billing import Invoice, InvoiceLine, Payment, Estimate, EstimateLine
from app.models.inventory import Product, ProductLot, StockMovement, Supplier
from app.models.controlled_substance import ControlledSubstanceEntry
from app.models.medical import (
    MedicalRecord, RecordType, Prescription, PrescriptionItem,
    ConsultationTemplate, ConsultationTemplateProduct, MedicalRecordProduct,
)
from app.models.hospitalization import Hospitalization, CareTask
from app.models.communication import Communication, ReminderRule

# ──────────────────── Realistic French data pools ────────────────────

FIRST_NAMES = [
    "Jean", "Pierre", "Marie", "Sophie", "Laurent", "Catherine", "Michel", "Isabelle",
    "Francois", "Nathalie", "Philippe", "Valerie", "Nicolas", "Sandrine", "Christophe",
    "Caroline", "Stephane", "Veronique", "Olivier", "Sylvie", "Thomas", "Celine",
    "Patrick", "Anne", "David", "Helene", "Eric", "Florence", "Alain", "Monique",
    "Bruno", "Christine", "Frederic", "Martine", "Guillaume", "Aurelie", "Thierry",
    "Julie", "Jerome", "Emilie", "Marc", "Pauline", "Benoit", "Delphine",
    "Antoine", "Claire", "Sebastien", "Lucie", "Romain", "Camille",
]

LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand",
    "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David",
    "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "Andre", "Lefevre",
    "Mercier", "Dupont", "Lambert", "Bonnet", "Francois", "Martinez", "Legrand",
    "Garnier", "Faure", "Rousseau", "Blanc", "Guerin", "Muller", "Henry", "Roussel",
    "Nicolas", "Perrin", "Morin", "Mathieu", "Clement", "Gauthier", "Dumont",
    "Lopez", "Fontaine", "Chevalier", "Robin",
]

CITIES = [
    ("Paris", "75001"), ("Lyon", "69001"), ("Marseille", "13001"), ("Toulouse", "31000"),
    ("Nantes", "44000"), ("Bordeaux", "33000"), ("Lille", "59000"), ("Rennes", "35000"),
    ("Strasbourg", "67000"), ("Montpellier", "34000"), ("Nice", "06000"),
    ("Grenoble", "38000"), ("Dijon", "21000"), ("Angers", "49000"), ("Tours", "37000"),
]

STREETS = [
    "Rue de la Paix", "Avenue des Champs-Elysees", "Boulevard Victor Hugo",
    "Rue du Commerce", "Avenue de la Republique", "Rue Pasteur", "Place de la Mairie",
    "Rue Jean Jaures", "Impasse des Lilas", "Allee des Tilleuls", "Chemin du Moulin",
    "Rue de la Liberte", "Rue Gambetta", "Avenue du General de Gaulle", "Rue Voltaire",
]

DOG_NAMES = [
    "Rex", "Max", "Buddy", "Charlie", "Rocky", "Oscar", "Luna", "Bella", "Nala",
    "Lola", "Kira", "Maya", "Sasha", "Caramel", "Filou", "Gribouille", "Milo",
    "Simba", "Balto", "Lucky", "Tango", "Zorro", "Cookie", "Noisette", "Cannelle",
]

CAT_NAMES = [
    "Minou", "Felix", "Garfield", "Tigrou", "Mistigri", "Caline", "Chipie", "Nala",
    "Simba", "Luna", "Minette", "Grisou", "Pacha", "Romeo", "Kitty", "Plume",
    "Filou", "Cleo", "Moustache", "Pistache", "Chaussette", "Biscuit", "Perle",
]

BIRD_NAMES = ["Piou-Piou", "Coco", "Kiwi", "Rio", "Perle", "Plume", "Bijou", "Zephyr"]
RABBIT_NAMES = ["Pompon", "Noisette", "Caramel", "Flocon", "Cannelle", "Cookie", "Choupi"]
NAC_NAMES = ["Speedy", "Bubulle", "Ecaille", "Zen", "Sushi", "Pixel", "Nemo"]

DOG_BREEDS = [
    "Labrador", "Golden Retriever", "Berger Allemand", "Bouledogue Francais",
    "Cavalier King Charles", "Beagle", "Yorkshire Terrier", "Caniche", "Cocker Anglais",
    "Border Collie", "Shih Tzu", "Jack Russell", "Husky Siberien", "Berger Australien",
    "Boxer", "Teckel", "Epagneul Breton", "Bichon Maltais", None,
]

CAT_BREEDS = [
    "Europeen", "Persan", "Siamois", "Maine Coon", "British Shorthair",
    "Bengal", "Ragdoll", "Sacre de Birmanie", "Chartreux", "Sphynx",
    "Abyssin", "Norvegien", None,
]

COLORS_ANIMALS = [
    "Noir", "Blanc", "Roux", "Gris", "Brun", "Tricolore", "Noir et blanc",
    "Fauve", "Tigre", "Creme", "Bleu", "Chocolat",
]

CONSULTATION_REASONS = [
    "Consultation de routine", "Vaccination annuelle", "Boiterie membre posterieur",
    "Vomissements depuis 2 jours", "Otite externe", "Toux persistante",
    "Perte de poids inexpliquee", "Dermatite allergique", "Plaie a la patte",
    "Diarrhee chronique", "Probleme dentaire", "Check-up senior",
    "Difficultees respiratoires", "Probleme urinaire", "Masse cutanee",
    "Prise de sang de controle", "Rappel vaccin", "Sterilisation",
    "Detartrage", "Castration",
]

# ──────────────────── Products ────────────────────

PRODUCTS_DATA = [
    # (name, reference, type, unit, purchase_price, selling_price, vat_rate, is_service, is_controlled)
    ("Consultation generale", "CONS-GEN", "service", "acte", None, 45.00, 20.0, True, False),
    ("Consultation urgence", "CONS-URG", "service", "acte", None, 75.00, 20.0, True, False),
    ("Vaccination chien", "VAC-CHIEN", "service", "acte", None, 55.00, 20.0, True, False),
    ("Vaccination chat", "VAC-CHAT", "service", "acte", None, 50.00, 20.0, True, False),
    ("Sterilisation chatte", "CHIR-STERF", "service", "acte", None, 180.00, 20.0, True, False),
    ("Sterilisation chien", "CHIR-STERM", "service", "acte", None, 220.00, 20.0, True, False),
    ("Castration chat", "CHIR-CASTC", "service", "acte", None, 120.00, 20.0, True, False),
    ("Castration chien", "CHIR-CASTD", "service", "acte", None, 160.00, 20.0, True, False),
    ("Detartrage", "DENT-DETAR", "service", "acte", None, 150.00, 20.0, True, False),
    ("Radiographie", "IMG-RADIO", "service", "acte", None, 65.00, 20.0, True, False),
    ("Echographie", "IMG-ECHO", "service", "acte", None, 85.00, 20.0, True, False),
    ("Analyse sanguine", "LAB-SANG", "service", "acte", None, 55.00, 20.0, True, False),
    ("Metacam 1.5mg/ml", "MED-META15", "medication", "ml", 8.50, 18.90, 20.0, False, False),
    ("Metacam 0.5mg/ml chat", "MED-METAC", "medication", "ml", 7.20, 16.50, 20.0, False, False),
    ("Amoxicilline 250mg", "MED-AMOX25", "medication", "comprime", 0.15, 0.45, 20.0, False, False),
    ("Amoxicilline 500mg", "MED-AMOX50", "medication", "comprime", 0.25, 0.65, 20.0, False, False),
    ("Rimadyl 100mg", "MED-RIMA", "medication", "comprime", 0.80, 1.90, 20.0, False, False),
    ("Frontline Combo chien M", "AP-FRONTM", "medication", "pipette", 4.50, 12.90, 20.0, False, False),
    ("Frontline Combo chat", "AP-FRONTC", "medication", "pipette", 3.80, 10.50, 20.0, False, False),
    ("Milbemax chien", "AP-MILBED", "medication", "comprime", 2.50, 7.90, 20.0, False, False),
    ("Milbemax chat", "AP-MILBEC", "medication", "comprime", 2.20, 6.90, 20.0, False, False),
    ("Cerenia 16mg", "MED-CEREN", "medication", "comprime", 3.50, 8.90, 20.0, False, False),
    ("Croquettes Royal Canin Vet Diet Renal", "FOOD-RC-REN", "food", "kg", 6.00, 12.50, 5.5, False, False),
    ("Croquettes Hill's i/d", "FOOD-HILL-ID", "food", "kg", 5.50, 11.90, 5.5, False, False),
    ("Collier elisabethain M", "SUP-COLEM", "supply", "unite", 2.00, 6.50, 20.0, False, False),
    ("Pansement adhesif", "SUP-PANS", "supply", "unite", 0.30, 1.50, 20.0, False, False),
    ("Seringue 5ml", "SUP-SER5", "supply", "unite", 0.10, 0.80, 20.0, False, False),
    ("Ketamine 100mg/ml", "CTRL-KETA", "medication", "ml", 5.00, 15.00, 20.0, False, True),
    ("Morphine 10mg/ml", "CTRL-MORPH", "medication", "ml", 8.00, 22.00, 20.0, False, True),
    ("Diazepam 5mg/ml", "CTRL-DIAZ", "medication", "ml", 3.00, 9.50, 20.0, False, True),
]

TEMPLATES_DATA = [
    ("Consultation generale", "general", None, "Motif de consultation", "Examen clinique complet - T°C, FC, FR, muqueuses, TRC, palpation abdominale", "A determiner", "Suivi selon evolution"),
    ("Vaccination chien", "vaccination", "dog", "Rappel vaccin annuel", "Bon etat general, absence d'anomalie", "Animal apte a la vaccination - CHPPiL administre", "Rappel dans 1 an"),
    ("Vaccination chat", "vaccination", "cat", "Rappel vaccin annuel", "Bon etat general", "Animal apte - Typhus/Coryza/Leucose administre", "Rappel dans 1 an"),
    ("Chirurgie - Sterilisation", "chirurgie", None, "Sterilisation programmee", "Examen pre-operatoire normal - Jeune respecte", "Ovariectomie / Orchiectomie realisee sans complication", "Retrait des fils J+10, Anti-inflammatoire 5 jours"),
    ("Dermatologie", "dermatologie", None, "Prurit / Lesions cutanees", "Lesions erythemateuses, depilations, raclage cutane realise", "Dermatite allergique / Pyodermite / A preciser", "Traitement topique + systemique, controle dans 15 jours"),
    ("Gastro-enterologie", "gastro", None, "Vomissements / Diarrhee", "Deshydratation legere, abdomen sensible a la palpation", "Gastro-enterite aigue", "Diete 24h puis alimentation digestible, anti-emetique si besoin"),
    ("Ophtalmologie", "ophtalmologie", None, "Oeil rouge / Ecoulement oculaire", "Test de Schirmer, test a la fluoresceine, PIO", "Conjonctivite / Ulcere corneen / A preciser", "Collyre antibiotique, controle dans 7 jours"),
    ("Check-up senior", "geriatrie", None, "Bilan de sante annuel animal age", "Examen complet + prise de sang + analyse urinaire", "Bilan a interpreter", "Suivi adapte selon resultats"),
    ("Urgence", "urgence", None, "Urgence - A preciser", "Examen d'urgence - Evaluation ABCDE", "A determiner en urgence", "Stabilisation et traitement"),
    ("Dentaire", "dentaire", None, "Halitose / Probleme dentaire", "Examen bucco-dentaire, tartre stade II-III", "Maladie parodontale", "Detartrage sous AG programme"),
]

# ──────────────────── Helpers ────────────────────

NOW = datetime.now()
ONE_YEAR_AGO = NOW - timedelta(days=365)
rng = random.Random(42)  # reproducible


def rand_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=rng.random() * delta)


def rand_date_only(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, max(delta, 1)))


def rand_phone():
    return f"06{rng.randint(10000000, 99999999)}"


def rand_invoice_number(i):
    return f"FAC-{NOW.year}-{i:05d}"


def rand_estimate_number(i):
    return f"DEV-{NOW.year}-{i:05d}"


# ──────────────────── Main seeder ────────────────────

def seed(db_url: str = None):
    url = db_url or settings.DATABASE_URL
    print(f"Connecting to database...")
    engine = create_engine(url, pool_pre_ping=True)
    # Do NOT call Base.metadata.create_all() — the app manages schema.
    # Tables must already exist (run the app at least once first).
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        _do_seed(db)
        db.commit()
        print("\nSeed complete!")
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()
        engine.dispose()


def _do_seed(db):
    # ── 1. Staff (skip if users already exist) ──
    existing_users = db.query(User).count()
    if existing_users > 0:
        print(f"Found {existing_users} existing users, reusing them as staff.")
        staff = db.query(User).filter(User.is_active == True).all()
        vets = [u for u in staff if u.role == UserRole.VETERINARIAN]
        if not vets:
            vets = staff[:1]  # fallback: use first user as vet
    else:
        print("No users found. Skipping user creation (users are managed by Supabase auth).")
        print("Please create at least one user via the app first, then re-run this script.")
        return

    all_staff = staff
    print(f"  Staff: {len(all_staff)} users ({len(vets)} vets)")

    # ── 2. Suppliers ──
    suppliers_data = [
        ("Centravet", "Jean Dupuis", "commandes@centravet.fr", "01 23 45 67 89"),
        ("Alcyon", "Marie Lambert", "contact@alcyon.fr", "01 98 76 54 32"),
        ("Coveto", "Pierre Moreau", "info@coveto.fr", "04 56 78 90 12"),
    ]
    suppliers = []
    for name, contact, email, phone in suppliers_data:
        s = Supplier(name=name, contact_name=contact, email=email, phone=phone)
        db.add(s)
        suppliers.append(s)
    db.flush()
    print(f"  Suppliers: {len(suppliers)}")

    # ── 3. Products ──
    products = []
    controlled_products = []
    service_products = []
    med_products = []
    for (name, ref, ptype, unit, pprice, sprice, vat, is_svc, is_ctrl) in PRODUCTS_DATA:
        p = Product(
            name=name, reference=ref,
            product_type=ptype,
            unit=unit,
            purchase_price=pprice,
            selling_price=sprice,
            vat_rate=vat,
            stock_quantity=0 if is_svc else rng.randint(20, 200),
            stock_alert_threshold=5,
            is_controlled_substance=is_ctrl,
            is_active=True,
            supplier_id=rng.choice(suppliers).id if not is_svc else None,
        )
        db.add(p)
        products.append(p)
        if is_ctrl:
            controlled_products.append(p)
        if is_svc:
            service_products.append(p)
        else:
            med_products.append(p)
    db.flush()
    print(f"  Products: {len(products)} ({len(service_products)} services, {len(controlled_products)} controlled)")

    # ── 4. Product lots ──
    lots_created = 0
    for p in med_products:
        for _ in range(rng.randint(1, 3)):
            lot = ProductLot(
                product_id=p.id,
                lot_number=f"LOT-{rng.randint(100000, 999999)}",
                expiry_date=date.today() + timedelta(days=rng.randint(60, 730)),
                quantity=rng.randint(10, 100),
                received_date=rand_date_only(ONE_YEAR_AGO.date(), date.today()),
            )
            db.add(lot)
            lots_created += 1
    db.flush()
    print(f"  Product lots: {lots_created}")

    # ── 5. Clients ──
    clients = []
    used_names = set()
    for _ in range(50):
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        key = f"{fn}_{ln}"
        while key in used_names:
            fn = rng.choice(FIRST_NAMES)
            ln = rng.choice(LAST_NAMES)
            key = f"{fn}_{ln}"
        used_names.add(key)
        city, postal = rng.choice(CITIES)
        c = Client(
            first_name=fn, last_name=ln,
            email=f"{fn.lower()}.{ln.lower()}@example.com",
            phone=rand_phone(), mobile=rand_phone(),
            address=f"{rng.randint(1, 120)} {rng.choice(STREETS)}",
            city=city, postal_code=postal, country="France",
            is_active=True,
            created_at=rand_date(ONE_YEAR_AGO, NOW),
        )
        db.add(c)
        clients.append(c)
    db.flush()
    print(f"  Clients: {len(clients)}")

    # ── 6. Animals ──
    animals = []
    species_weights = [("dog", 45), ("cat", 35), ("bird", 5), ("rabbit", 5), ("reptile", 3), ("nac", 4), ("horse", 2), ("other", 1)]
    species_list = []
    for sp, w in species_weights:
        species_list.extend([sp] * w)

    for client in clients:
        n_animals = rng.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]
        for _ in range(n_animals):
            sp = rng.choice(species_list)
            if sp == "dog":
                name = rng.choice(DOG_NAMES)
                breed = rng.choice(DOG_BREEDS)
            elif sp == "cat":
                name = rng.choice(CAT_NAMES)
                breed = rng.choice(CAT_BREEDS)
            elif sp == "bird":
                name = rng.choice(BIRD_NAMES)
                breed = None
            elif sp == "rabbit":
                name = rng.choice(RABBIT_NAMES)
                breed = None
            else:
                name = rng.choice(NAC_NAMES)
                breed = None

            age_days = rng.randint(90, 365 * 15)
            dob = date.today() - timedelta(days=age_days)
            sex = rng.choice(["male", "female", "unknown"])
            vital = "alive"
            vital_date = None
            is_deceased = False
            deceased_date = None

            # ~5% deceased, ~2% lost
            r = rng.random()
            if r < 0.05:
                vital = "deceased"
                is_deceased = True
                d = rand_date_only(ONE_YEAR_AGO.date(), date.today())
                vital_date = d
                deceased_date = d
            elif r < 0.07:
                vital = "lost"
                vital_date = rand_date_only(ONE_YEAR_AGO.date(), date.today())

            a = Animal(
                client_id=client.id, name=name, species=sp,
                breed=breed, sex=sex, date_of_birth=dob,
                color=rng.choice(COLORS_ANIMALS),
                microchip_number=f"{rng.randint(250000000000000, 259999999999999)}" if rng.random() > 0.2 else None,
                is_neutered=rng.random() > 0.5,
                vital_status=vital, vital_status_date=vital_date,
                is_deceased=is_deceased, deceased_date=deceased_date,
                created_at=rand_date(ONE_YEAR_AGO, NOW),
            )
            db.add(a)
            animals.append(a)
    db.flush()
    print(f"  Animals: {len(animals)}")

    # ── 7. Animal alerts (~10%) ──
    alert_types = ["allergy", "aggressive", "escape_risk", "medical"]
    alert_messages = {
        "allergy": ["Allergie penicilline", "Allergie AINS", "Allergie latex"],
        "aggressive": ["Animal mordeur - Museliere obligatoire", "Chat griffeur", "Prudence manipulation"],
        "escape_risk": ["Risque de fuite en consultation", "Attacher en double laisse"],
        "medical": ["Epileptique - traitement en cours", "Insuffisance renale chronique", "Diabetique"],
    }
    alerts_created = 0
    for a in animals:
        if rng.random() < 0.10:
            at = rng.choice(alert_types)
            db.add(AnimalAlert(
                animal_id=a.id, alert_type=at,
                message=rng.choice(alert_messages[at]),
                severity=rng.choice(["low", "medium", "high"]),
                is_active=True,
            ))
            alerts_created += 1
    db.flush()
    print(f"  Animal alerts: {alerts_created}")

    # ── 8. Weight records ──
    weights_created = 0
    for a in animals:
        if a.species in ("dog", "cat") and rng.random() < 0.4:
            base_weight = rng.uniform(3, 40) if a.species == "dog" else rng.uniform(2.5, 7)
            n_records = rng.randint(2, 6)
            for j in range(n_records):
                w = round(base_weight + rng.uniform(-1, 1), 1)
                db.add(WeightRecord(
                    animal_id=a.id, weight_kg=max(0.5, w),
                    recorded_at=rand_date(ONE_YEAR_AGO, NOW),
                    recorded_by_id=rng.choice(all_staff).id,
                ))
                weights_created += 1
    db.flush()
    print(f"  Weight records: {weights_created}")

    # ── 9. Appointments (~300) ──
    alive_animals = [a for a in animals if a.vital_status == "alive"]
    appointments = []
    appt_types = list(AppointmentType)
    appt_type_weights = [40, 10, 5, 20, 10, 3, 12]  # consultation heavy

    for i in range(300):
        animal = rng.choice(alive_animals)
        client = next(c for c in clients if c.id == animal.client_id)
        vet = rng.choice(vets)
        atype = rng.choices(appt_types, weights=appt_type_weights)[0]
        start = rand_date(ONE_YEAR_AGO, NOW + timedelta(days=30))
        # round to 15-min slots
        start = start.replace(minute=(start.minute // 15) * 15, second=0, microsecond=0)
        # only during work hours 8-19
        start = start.replace(hour=rng.randint(8, 18))
        duration = 30 if atype in (AppointmentType.CONSULTATION, AppointmentType.VACCINATION, AppointmentType.CHECKUP) else 60
        end = start + timedelta(minutes=duration)

        if start < NOW - timedelta(hours=2):
            r = rng.random()
            if r < 0.70:
                status = AppointmentStatus.COMPLETED
            elif r < 0.80:
                status = AppointmentStatus.CANCELLED
            elif r < 0.85:
                status = AppointmentStatus.NO_SHOW
            else:
                status = AppointmentStatus.COMPLETED
        else:
            status = rng.choice([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])

        appt = Appointment(
            client_id=client.id, animal_id=animal.id, veterinarian_id=vet.id,
            appointment_type=atype, status=status,
            start_time=start, end_time=end,
            reason=rng.choice(CONSULTATION_REASONS),
            created_at=start - timedelta(days=rng.randint(1, 14)),
        )
        db.add(appt)
        appointments.append(appt)
    db.flush()
    print(f"  Appointments: {len(appointments)}")

    # ── 10. Medical records for completed appointments ──
    completed_appts = [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
    med_records = []
    record_type_map = {
        AppointmentType.CONSULTATION: RecordType.CONSULTATION,
        AppointmentType.VACCINATION: RecordType.VACCINATION,
        AppointmentType.SURGERY: RecordType.SURGERY,
        AppointmentType.EMERGENCY: RecordType.CONSULTATION,
        AppointmentType.CHECKUP: RecordType.CONSULTATION,
        AppointmentType.GROOMING: RecordType.NOTE,
        AppointmentType.OTHER: RecordType.NOTE,
    }

    for appt in completed_appts[:200]:
        rtype = record_type_map.get(appt.appointment_type, RecordType.CONSULTATION)
        mr = MedicalRecord(
            animal_id=appt.animal_id, veterinarian_id=appt.veterinarian_id,
            appointment_id=appt.id, record_type=rtype,
            subjective=rng.choice(CONSULTATION_REASONS),
            objective="Examen clinique: T 38.5C, FC 80/min, FR 20/min, muqueuses roses, TRC < 2s" if rng.random() > 0.3 else None,
            assessment="RAS" if rng.random() > 0.5 else "A surveiller",
            plan="Traitement symptomatique" if rng.random() > 0.5 else None,
            created_at=appt.start_time,
        )
        db.add(mr)
        med_records.append(mr)
    db.flush()
    print(f"  Medical records: {len(med_records)}")

    # ── 11. Invoices ──
    invoices = []
    for i, appt in enumerate(completed_appts[:200]):
        client = next(c for c in clients if c.id == appt.client_id)
        # Pick 1-3 products for the invoice
        n_lines = rng.randint(1, 3)
        line_products = []
        # Always include the consultation service
        consult_product = next((p for p in service_products if "generale" in p.name.lower()), service_products[0])
        line_products.append((consult_product, 1))
        for _ in range(n_lines - 1):
            p = rng.choice(products)
            q = rng.randint(1, 5) if p.product_type != "service" else 1
            line_products.append((p, q))

        subtotal = Decimal("0")
        total_vat = Decimal("0")
        lines_to_add = []
        for prod, qty in line_products:
            unit_price = Decimal(str(prod.selling_price))
            vat = Decimal(str(prod.vat_rate or 20))
            lt = unit_price * qty
            subtotal += lt
            total_vat += lt * vat / 100
            lines_to_add.append((prod, qty, unit_price, vat, lt))

        total = subtotal + total_vat
        # Determine payment status
        r = rng.random()
        if r < 0.60:
            status = "paid"
            amount_paid = total
        elif r < 0.80:
            status = "partial"
            amount_paid = round(total * Decimal(str(rng.uniform(0.2, 0.8))), 2)
        else:
            status = "sent"
            amount_paid = Decimal("0")

        inv = Invoice(
            invoice_number=rand_invoice_number(i + 1),
            client_id=client.id, animal_id=appt.animal_id,
            status=status,
            issue_date=appt.start_time.date(),
            due_date=appt.start_time.date() + timedelta(days=30),
            subtotal=round(subtotal, 2),
            total_vat=round(total_vat, 2),
            total=round(total, 2),
            amount_paid=round(amount_paid, 2),
            created_by_id=appt.veterinarian_id,
            created_at=appt.start_time,
        )
        db.add(inv)
        db.flush()

        for prod, qty, up, vat, lt in lines_to_add:
            db.add(InvoiceLine(
                invoice_id=inv.id, product_id=prod.id,
                description=prod.name, quantity=qty,
                unit_price=up, vat_rate=vat, line_total=lt,
            ))

        # Payments
        if amount_paid > 0:
            method = rng.choice(["card", "cash", "check", "transfer"])
            db.add(Payment(
                invoice_id=inv.id, amount=amount_paid,
                payment_method=method,
                payment_date=appt.start_time.date() + timedelta(days=rng.randint(0, 7)),
                received_by_id=rng.choice(all_staff).id,
            ))

        invoices.append(inv)
    db.flush()
    print(f"  Invoices: {len(invoices)} (with lines and payments)")

    # ── 12. Stock movements ──
    movements_created = 0
    for p in med_products:
        # Initial stock entry
        db.add(StockMovement(
            product_id=p.id, movement_type="in",
            quantity=rng.randint(50, 200),
            reason="Stock initial",
            reference_type="manual",
            performed_by_id=rng.choice(all_staff).id,
            created_at=ONE_YEAR_AGO,
        ))
        movements_created += 1
        # A few restocks throughout the year
        for _ in range(rng.randint(1, 4)):
            db.add(StockMovement(
                product_id=p.id, movement_type="in",
                quantity=rng.randint(20, 100),
                reason="Reapprovisionnement",
                reference_type="manual",
                performed_by_id=rng.choice(all_staff).id,
                created_at=rand_date(ONE_YEAR_AGO, NOW),
            ))
            movements_created += 1
        # Consumption
        for _ in range(rng.randint(3, 15)):
            db.add(StockMovement(
                product_id=p.id, movement_type="out",
                quantity=rng.randint(1, 10),
                reason="Utilisation consultation",
                reference_type="invoice",
                performed_by_id=rng.choice(all_staff).id,
                created_at=rand_date(ONE_YEAR_AGO, NOW),
            ))
            movements_created += 1
    db.flush()
    print(f"  Stock movements: {movements_created}")

    # ── 13. Controlled substance entries ──
    cs_created = 0
    for cp in controlled_products:
        remaining = Decimal("100")
        # Initial stock
        db.add(ControlledSubstanceEntry(
            product_id=cp.id, date=ONE_YEAR_AGO.date(),
            movement_type="in", quantity=100,
            lot_number=f"LOT-CS-{rng.randint(1000, 9999)}",
            remaining_stock=remaining,
            notes="Stock initial",
        ))
        cs_created += 1

        # Dispensing events
        for _ in range(rng.randint(5, 20)):
            animal = rng.choice(alive_animals)
            client = next(c for c in clients if c.id == animal.client_id)
            qty = round(rng.uniform(0.5, 5), 1)
            remaining -= Decimal(str(qty))
            if remaining < 0:
                # Restock
                remaining += Decimal("100")
                db.add(ControlledSubstanceEntry(
                    product_id=cp.id,
                    date=rand_date_only(ONE_YEAR_AGO.date(), date.today()),
                    movement_type="in", quantity=100,
                    lot_number=f"LOT-CS-{rng.randint(1000, 9999)}",
                    remaining_stock=remaining,
                    notes="Reapprovisionnement",
                ))
                cs_created += 1

            dosage_val = f"{round(rng.uniform(0.1, 2.0), 2)} mg/kg"
            db.add(ControlledSubstanceEntry(
                product_id=cp.id,
                date=rand_date_only(ONE_YEAR_AGO.date(), date.today()),
                movement_type="prescription", quantity=qty,
                patient_animal_id=animal.id,
                patient_owner_name=f"{client.first_name} {client.last_name}",
                prescribing_vet_id=rng.choice(vets).id,
                reason=rng.choice(["Analgesie", "Sedation", "Anesthesie", "Douleur chronique"]),
                dosage=dosage_val,
                total_delivered=round(qty * rng.uniform(1, 5), 2),
                remaining_stock=max(remaining, Decimal("0")),
            ))
            cs_created += 1
    db.flush()
    print(f"  Controlled substance entries: {cs_created}")

    # ── 14. Consultation templates ──
    templates = []
    for name, cat, sp, subj, obj, assess, plan_text in TEMPLATES_DATA:
        t = ConsultationTemplate(
            name=name, category=cat, species=sp,
            subjective=subj, objective=obj, assessment=assess, plan=plan_text,
            is_active=True,
            created_by_id=rng.choice(all_staff).id,
        )
        db.add(t)
        templates.append(t)
    db.flush()
    # Add some template products
    tp_created = 0
    for t in templates:
        n_prods = rng.randint(0, 3)
        chosen = rng.sample(products, min(n_prods, len(products)))
        for p in chosen:
            db.add(ConsultationTemplateProduct(
                template_id=t.id, product_id=p.id,
                quantity=rng.randint(1, 3),
                treatment_location=rng.choice(["onsite", "home"]),
            ))
            tp_created += 1
    db.flush()
    print(f"  Templates: {len(templates)} (with {tp_created} product links)")

    # ── 15. Hospitalizations (~10) ──
    hosps_created = 0
    for _ in range(10):
        animal = rng.choice(alive_animals)
        vet = rng.choice(vets)
        admitted = rand_date(ONE_YEAR_AGO, NOW - timedelta(days=1))
        discharged = admitted + timedelta(days=rng.randint(1, 7)) if rng.random() > 0.2 else None
        status = "discharged" if discharged else "active"
        h = Hospitalization(
            animal_id=animal.id, veterinarian_id=vet.id,
            status=status,
            reason=rng.choice(["Chirurgie programmee", "Surveillance post-op", "Pancreatite", "Fracture", "Pyometre"]),
            admitted_at=admitted,
            discharged_at=discharged,
            cage_number=f"C{rng.randint(1, 12)}",
        )
        db.add(h)
        db.flush()

        # Care tasks
        n_tasks = rng.randint(3, 10)
        for j in range(n_tasks):
            scheduled = admitted + timedelta(hours=rng.randint(1, 168))
            is_done = scheduled < NOW and rng.random() > 0.1
            db.add(CareTask(
                hospitalization_id=h.id,
                scheduled_at=scheduled,
                task_type=rng.choice(["medication", "vitals", "feeding", "observation"]),
                description=rng.choice([
                    "Prise de temperature", "Administration Metacam", "Repas",
                    "Observation comportement", "Changement pansement", "Prise de sang controle",
                ]),
                is_completed=is_done,
                completed_at=scheduled + timedelta(minutes=rng.randint(0, 30)) if is_done else None,
                completed_by_id=rng.choice(all_staff).id if is_done else None,
            ))
        hosps_created += 1
    db.flush()
    print(f"  Hospitalizations: {hosps_created}")

    # ── 16. Communications ──
    comms_created = 0
    for _ in range(30):
        client = rng.choice(clients)
        channel = rng.choice(["email", "sms"])
        sent = rand_date(ONE_YEAR_AGO, NOW)
        db.add(Communication(
            client_id=client.id, channel=channel,
            subject="Rappel vaccin" if channel == "email" else None,
            body=rng.choice([
                "Bonjour, le vaccin de votre animal arrive a echeance. Merci de prendre rendez-vous.",
                "Rappel: votre rendez-vous est programme demain.",
                "N'oubliez pas le traitement antiparasitaire de votre compagnon.",
            ]),
            status=rng.choice(["sent", "delivered"]),
            sent_at=sent,
            created_at=sent,
        ))
        comms_created += 1
    db.flush()
    print(f"  Communications: {comms_created}")

    # ── 17. Reminder rules ──
    rules = [
        ("Rappel vaccin chien", "vaccine", "dog", "email", 30, 7, 1),
        ("Rappel vaccin chat", "vaccine", "cat", "email", 30, 7, 1),
        ("Rappel antiparasitaire", "antiparasitic", None, "sms", 7, 3, 1),
        ("Check-up senior", "checkup", None, "email", 60, 30, 7),
    ]
    for name, rtype, species, channel, d1, d2, d3 in rules:
        db.add(ReminderRule(
            name=name, reminder_type=rtype, species=species, channel=channel,
            days_before=d1, days_before_second=d2, days_after=d3,
            is_active=True,
        ))
    db.flush()
    print(f"  Reminder rules: {len(rules)}")

    # ── 18. Estimates (~20) ──
    estimates_created = 0
    for i in range(20):
        client = rng.choice(clients)
        animal = rng.choice([a for a in animals if a.client_id == client.id] or alive_animals)
        n_lines = rng.randint(1, 4)
        subtotal = Decimal("0")
        total_vat = Decimal("0")
        est_lines = []
        for _ in range(n_lines):
            p = rng.choice(products)
            qty = rng.randint(1, 3)
            up = Decimal(str(p.selling_price))
            vat = Decimal(str(p.vat_rate or 20))
            lt = up * qty
            subtotal += lt
            total_vat += lt * vat / 100
            est_lines.append((p, qty, up, vat, lt))

        total = subtotal + total_vat
        issue = rand_date_only(ONE_YEAR_AGO.date(), date.today())
        est = Estimate(
            estimate_number=rand_estimate_number(i + 1),
            client_id=client.id, animal_id=animal.id,
            status=rng.choice(["draft", "sent", "accepted", "rejected"]),
            issue_date=issue,
            valid_until=issue + timedelta(days=30),
            subtotal=round(subtotal, 2), total_vat=round(total_vat, 2), total=round(total, 2),
            created_by_id=rng.choice(all_staff).id,
        )
        db.add(est)
        db.flush()
        for p, qty, up, vat, lt in est_lines:
            db.add(EstimateLine(
                estimate_id=est.id, product_id=p.id,
                description=p.name, quantity=qty,
                unit_price=up, vat_rate=vat, line_total=lt,
            ))
        estimates_created += 1
    db.flush()
    print(f"  Estimates: {estimates_created}")

    print(f"\n--- Summary ---")
    print(f"  Clients: {len(clients)}")
    print(f"  Animals: {len(animals)}")
    print(f"  Appointments: {len(appointments)}")
    print(f"  Invoices: {len(invoices)}")
    print(f"  Products: {len(products)}")


if __name__ == "__main__":
    seed()
