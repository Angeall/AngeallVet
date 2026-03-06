# AngeallVet - Système de Gestion Vétérinaire (PMS)

Application métier complète pour cliniques vétérinaires. Gestion des patients, rendez-vous, dossiers médicaux, stocks, facturation et communications.

## Modules

| Module | Description |
|--------|-------------|
| **CRM & Patients** | Fiches clients/animaux, alertes visuelles, courbe de poids, fusion de doublons |
| **Agenda** | RDV avec codes couleurs, salle d'attente virtuelle, types de consultation |
| **Dossier Médical (EMR)** | Format SOAP, templates de consultation, prescriptions, pièces jointes |
| **Stocks & Pharmacie** | Traçabilité des lots, dates de péremption, alertes stock bas, fournisseurs |
| **Facturation** | Devis → Facture en 1 clic, multi-taux TVA, paiements, déstockage auto |
| **Communications** | Historique emails/SMS, règles de rappel vaccins (J-30, J-7, J+1) |
| **Hospitalisation** | Feuille de soins numérique, tâches planifiées, suivi en temps réel |
| **RBAC** | Admin, Vétérinaire, ASV, Comptable avec droits différenciés |

## Stack Technique

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL
- **Frontend**: React 18, React Router, Recharts, FullCalendar
- **Auth**: Supabase Auth (JWT, sessions, MFA-ready), RBAC local
- **Infra**: Docker Compose

## Démarrage Rapide

### Prérequis : Supabase

1. Créer un projet sur [supabase.com](https://supabase.com)
2. Récupérer dans **Settings > API** :
   - `SUPABASE_URL` (Project URL)
   - `SUPABASE_ANON_KEY` (anon public key)
   - `SUPABASE_SERVICE_ROLE_KEY` (service_role key)
   - `SUPABASE_JWT_SECRET` (JWT Secret, dans Settings > API > JWT Settings)

### Avec Docker

```bash
cp .env.example .env
# Remplir les clés Supabase dans .env
docker-compose up -d
```

### Sans Docker

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Démarrer le serveur
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

### Données de démo

```bash
cd backend
python -m app.seed_demo
```

Comptes de démonstration :
| Rôle | Email | Mot de passe |
|------|-------|-------------|
| Admin | admin@angeallvet.fr | admin123 |
| Vétérinaire | dr.dupont@angeallvet.fr | vet123 |
| ASV | asv@angeallvet.fr | asv123 |
| Comptable | compta@angeallvet.fr | compta123 |

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Tests

```bash
cd backend
pytest
pytest --cov=app
```

## Structure du Projet

```
AngeallVet/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/    # Routes API (auth, clients, animals, etc.)
│   │   ├── core/             # Config, DB, sécurité
│   │   ├── models/           # Modèles SQLAlchemy
│   │   ├── schemas/          # Schémas Pydantic
│   │   ├── services/         # Logique métier
│   │   ├── main.py           # Point d'entrée FastAPI
│   │   └── seed_demo.py      # Données de démo
│   ├── tests/                # Tests unitaires
│   └── alembic/              # Migrations DB
├── frontend/
│   ├── src/
│   │   ├── components/       # Composants React
│   │   ├── pages/            # Pages de l'application
│   │   ├── services/         # Client API (axios)
│   │   ├── contexts/         # Contextes React (Auth)
│   │   └── styles/           # CSS
│   └── public/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Configuration (.env)

Toutes les variables de configuration sont dans `.env.example`. Copier vers `.env` et ajuster avant déploiement.

Variables clés :
- `DATABASE_URL` : Connexion PostgreSQL (base applicative, pas la base Supabase)
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET` : Auth Supabase
- `REACT_APP_SUPABASE_URL` / `REACT_APP_SUPABASE_ANON_KEY` : Auth côté frontend
- `SMTP_*` : Configuration email pour les rappels
- `SMS_*` : Configuration SMS (Twilio)
- `STRIPE_*` : Intégration paiement
- `GOOGLE_*` : Synchronisation Google Calendar

## Conformité RGPD

- Chiffrement des données sensibles configurable via `ENCRYPTION_KEY`
- Rétention des données configurable via `DATA_RETENTION_YEARS`
- Suppression logique (soft delete) des clients
- Journalisation des accès via les tokens JWT Supabase
- Authentification déléguée à Supabase (pas de stockage local de mots de passe)
