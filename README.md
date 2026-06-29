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
- **Auth**: PocketBase **tenant-local** (1 instance par tenant) + JWT applicatif signé par tenant, RBAC local
- **Multi-tenant**: résolution par sous-domaine, base PostgreSQL dédiée par tenant
- **Infra**: Docker Compose + reverse-proxy Caddy

## Démarrage Rapide

### Avec Docker (recommandé)

Tout est orchestré par Docker Compose : PostgreSQL, **PocketBase** (auth), le
backend, le frontend et un reverse-proxy **Caddy** qui assure la résolution des
tenants par sous-domaine.

```bash
cp .env.example .env
# Ajuster APP_SECRET_KEY, DB_PASSWORD, POCKETBASE_ADMIN_* et INITIAL_ADMIN_* dans .env
docker compose up -d
```

Au premier démarrage, tout est automatique :
- PocketBase crée son **superuser** à partir de `POCKETBASE_ADMIN_EMAIL` / `POCKETBASE_ADMIN_PASSWORD` ;
- le backend crée le **compte admin initial** (`INITIAL_ADMIN_*`) si la base est vide.

> Migration depuis une base existante (ère Supabase) : les utilisateurs déjà en base sont reliés à PocketBase **par email** à la première connexion. Il faut donc (re)créer leurs comptes côté PocketBase (admin UI `http://localhost:8090/_/` ou API superuser) avec le même email.

Accès :
- Application : `http://app.angeallvet.localhost` (tenant par défaut)
- Un tenant : `http://<slug>.angeallvet.localhost`
- PocketBase admin : `http://localhost:8090/_/`

> Les navigateurs résolvent automatiquement `*.localhost` vers `127.0.0.1`.
> En production, remplacez `:80` par votre domaine dans le `Caddyfile`
> (TLS automatique) et déclarez chaque tenant dans la table `tenants`.

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
# Dev direct (sans reverse-proxy) : viser les services locaux
printf "VITE_API_URL=http://localhost:8000/api/v1\nVITE_POCKETBASE_URL=http://localhost:8090\n" > .env.local
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
- `DATABASE_URL` : Connexion PostgreSQL (base du tenant par défaut / registre `tenants`)
- `APP_SECRET_KEY` : secret racine dont dérive le secret JWT de chaque tenant
- `POCKETBASE_URL` : URL interne de PocketBase (tenant par défaut)
- `POCKETBASE_ADMIN_EMAIL` / `POCKETBASE_ADMIN_PASSWORD` : superuser PocketBase utilisé par le backend pour gérer les utilisateurs
- `BASE_DOMAIN` / `DEFAULT_TENANT_SLUG` : résolution des tenants par sous-domaine
- `VITE_API_URL` / `VITE_POCKETBASE_URL` (frontend) : endpoints API et PocketBase (vides derrière Caddy = même origine)
- `SMTP_*` : Configuration email pour les rappels
- `SMS_*` : Configuration SMS (Twilio)
- `STRIPE_*` : Intégration paiement
- `GOOGLE_*` : Synchronisation Google Calendar

## Conformité RGPD

- Chiffrement des données sensibles configurable via `ENCRYPTION_KEY`
- Rétention des données configurable via `DATA_RETENTION_YEARS`
- Suppression logique (soft delete) des clients
- Journalisation des accès via les JWT applicatifs (signés par tenant)
- Authentification déléguée à PocketBase **tenant-local** (mots de passe jamais stockés par l'application ; ségrégation des identités par tenant)
