# Modules payants & licences — guide du déployeur

Ce guide explique comment **débloquer un module payant** (`sms`, `invoice_ninja`,
`google_calendar`) pour une clinique, via une **licence signée** déposée dans son
`.env`.

> **Deux choses distinctes**
> - **La licence** = *le droit* d'utiliser un module (l'« abonnement »). Elle est
>   signée par toi et infalsifiable.
> - **La configuration** = *les identifiants du service* (token Invoice Ninja,
>   clés Twilio, OAuth Google…). La licence ne contient **aucun** identifiant ;
>   elle ne fait qu'ouvrir l'accès.
>
> Un module ne fonctionne que si **les deux** sont en place.

Modules disponibles (clés exactes) : `sms`, `invoice_ninja`, `google_calendar`,
`accounting`.

---

## Pourquoi une licence signée et pas un simple `MODULE_SMS=true`

Chaque clinique a son propre `.env`. Un booléen y serait trivialement modifiable
par quiconque a accès au serveur. À la place, **toi seul** signes une licence avec
une **clé privée Ed25519 qui ne quitte jamais ta machine**. L'application ne
détient que la **clé publique** : elle peut *vérifier* une licence mais jamais en
*forger* une. Éditer le `.env` pour s'octroyer un module est donc inutile.

---

## Étape 0 — Une seule fois : générer la paire de clés

Depuis `backend/` (venv activé), ou via le conteneur Docker :

```bash
# en local
venv/Scripts/python.exe -m app.licensing keygen      # Windows
# ou
python -m app.licensing keygen

# ou directement dans le conteneur
docker compose exec backend python -m app.licensing keygen
```

La commande affiche :

1. **PRIVATE KEY** → enregistre-la dans `private.pem` et **garde-la hors des
   serveurs** (c'est elle qui signe les licences). Ne la commit jamais.
2. **PUBLIC KEY** → c'est `LICENSE_PUBLIC_KEY`. La **même** clé publique va dans le
   `.env` de **toutes** les cliniques.
3. Une version « une ligne » prête pour le `.env` :
   ```env
   LICENSE_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"
   ```

> Tant que `LICENSE_PUBLIC_KEY` est **vide**, on est en mode dev : **tous les
> modules sont actifs** (pratique pour développer/tester). Dès qu'une clé publique
> est présente, les modules viennent **strictement** de la licence.

---

## Étape 1 — Signer une licence pour une clinique

Sur **ta** machine (là où se trouve `private.pem`) :

```bash
python -m app.licensing sign \
  --key private.pem \
  --tenant clinique-martin \
  --modules sms,invoice_ninja \
  --max-users 5 \
  --days 365
```

Sortie : **le jeton de licence** (une longue chaîne) à coller dans le `.env`.

| Option | Rôle |
|---|---|
| `--key` | chemin vers la clé **privée** (ou `-` pour stdin) |
| `--modules` | liste séparée par des virgules : `sms`, `invoice_ninja`, `google_calendar`, `accounting`. Optionnel si `--max-users` est fourni (licence « plafond seul ») |
| `--tenant` | **lie** la licence à ce *slug* (anti-copie : la licence de la clinique A ne marche pas chez B). Doit correspondre au `DEFAULT_TENANT_SLUG` de la clinique — voir étape 2 |
| `--max-users` | nombre max d'utilisateurs actifs (admin inclus). Omettre = illimité |
| `--days` | validité en jours. Omettre = permanente |

Exemples :

```bash
# Uniquement les SMS, 3 sièges, 1 an
python -m app.licensing sign --key private.pem --tenant cabinet-durand --modules sms --max-users 3 --days 365

# Tous les modules, sièges illimités, permanente
python -m app.licensing sign --key private.pem --tenant clinique-lac --modules sms,invoice_ninja,google_calendar

# Plafond de sièges seul, sans module payant
python -m app.licensing sign --key private.pem --tenant petite-clinique --max-users 2
```

---

## Étape 2 — Installer la licence dans le `.env` de la clinique

Dans le `.env` du stack Docker de la clinique :

```env
# La clé publique (la même partout)
LICENSE_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"

# Le jeton signé pour CETTE clinique (sortie de l'étape 1)
LICENSE="eyJhbGciOiJFZERTQSJ9.....signature"

# Doit correspondre au --tenant utilisé pour signer (sinon la licence est refusée)
DEFAULT_TENANT_SLUG=clinique-martin
```

Puis recharger le backend :

```bash
docker compose restart backend
```

> Si tu signes **sans** `--tenant`, la licence n'est pas liée et fonctionne quel
> que soit le slug (pratique, mais aucune protection anti-copie).

---

## Étape 3 — Configurer le service du module

La licence **ouvre l'accès** ; il reste à brancher le service.

### `sms` — identifiants Twilio (dans le `.env`)

```env
SMS_PROVIDER=twilio
SMS_API_KEY=ACxxxxxxxxxxxxxxxx       # Account SID
SMS_API_SECRET=xxxxxxxxxxxxxxxx      # Auth Token
SMS_FROM_NUMBER=+32470000000
```

- **Sans le module `sms`** : le canal SMS est refusé (403) — seul l'e-mail
  fonctionne, même si les clés Twilio sont présentes.
- **Avec le module mais sans clés** : l'envoi échoue proprement (« SMS non
  configuré »).

### `invoice_ninja` — URL + token (dans l'application)

Dans l'app : **Paramètres → Facturation électronique (Invoice Ninja)** → renseigner
l'**URL de l'instance** et le **token API**.

- **Sans le module** : les factures/devis sortent en **PDF simple gratuit** (la
  section Invoice Ninja est masquée).
- **Avec le module + configuré** : bouton « Envoyer via Invoice Ninja » + PDF
  conforme + e-invoicing Peppol (B2B).

### `google_calendar` — OAuth (dans le `.env`, niveau déployeur)

```env
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxx
GOOGLE_REDIRECT_URI=https://<domaine-clinique>/api/v1/agenda/google/callback
```

Le flux iCal (abonnement lecture seule) ne demande **aucune** config
supplémentaire ; l'OAuth bidirectionnel demande les clés ci-dessus.

### `accounting` — rien à configurer

Aucun identifiant de service : la licence débloque simplement la page
**Comptabilité** (clôture de caisse + export journal/FEC), accessible aux rôles
**admin** et **comptable**. Une fois une journée clôturée, plus aucun
encaissement ne peut y être ajouté (intégrité).

---

## Vérifier que c'est bon

1. **Décoder le jeton** (sans vérifier la signature) pour relire son contenu :
   ```bash
   python -m app.licensing inspect --token "eyJ....."
   # -> { "modules": ["invoice_ninja","sms"], "sub": "clinique-martin",
   #      "max_users": 5, "exp": 1814364138, ... }
   ```
2. **Dans l'app** : se reconnecter (la session porte les modules), puis vérifier
   que les boutons/sections apparaissent (option SMS dans Communications, section
   Invoice Ninja dans Paramètres, bouton Google Agenda…).
3. **Côté API** : `GET /api/v1/auth/modules` renvoie `modules`, `max_users` et
   `user_count`.

---

## Modifier, renouveler ou révoquer

- **Ajouter/retirer un module, changer le plafond, prolonger** : signe une
  **nouvelle** licence et remplace `LICENSE` dans le `.env`, puis
  `docker compose restart backend`.
- **Révoquer** : il n'y a pas de révocation à distance. Utilise une **durée**
  (`--days`) adaptée à l'abonnement, ou re-signe/retire la licence.
- **Stack multi-tenant centralisé** (plusieurs cliniques derrière un même
  backend) : au lieu du `.env`, pose la licence sur la ligne du tenant via
  `PUT /api/v1/auth/tenants/{id}/license` (en-tête `X-Platform-Admin-Token`).

---

## Dépannage

| Symptôme | Vérifier |
|---|---|
| Un module reste inactif malgré la licence | `LICENSE_PUBLIC_KEY` bien présent ? `LICENSE` collé en entier (pas de retour à la ligne cassé) ? Backend redémarré ? |
| « Licence refusée : liée au tenant … » dans les logs | `DEFAULT_TENANT_SLUG` doit être **identique** au `--tenant` de la signature |
| Licence ignorée / expirée | `--days` dépassé ? Reslogner avec une nouvelle échéance |
| Tous les modules sont actifs sans licence | Normal en **dev** : `LICENSE_PUBLIC_KEY` est vide. En production, renseigne la clé publique |
| Le module est actif mais l'envoi échoue | C'est la **config** du service qui manque (clés Twilio, URL/token Invoice Ninja…) — voir étape 3 |

---

Détails techniques (code) : voir la section *Paid modules (licensing)* de
[`CLAUDE.md`](../CLAUDE.md) et `backend/app/core/licensing.py`.
