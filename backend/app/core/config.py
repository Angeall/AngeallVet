from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AngeallVet"
    # Secure by default: an unset APP_ENV is treated as production (fails closed
    # on insecure secrets, enforces the license, hides Swagger). Local dev /
    # tests MUST opt in with APP_ENV=development (docker-compose sets it; the
    # test suite sets it in conftest).
    APP_ENV: str = "production"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str = "dev-secret-key"
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = '["http://localhost:3000"]'

    # Database (central / registry database — holds the `tenants` table and,
    # for the default tenant, all application data)
    DATABASE_URL: str = "postgresql://angeallvet:angeallvet_dev@localhost:5432/angeallvet"

    # --- Multi-tenant resolution ---------------------------------------
    # Requests are routed to a tenant by the sub-domain of BASE_DOMAIN
    # (e.g. clinique-martin.angeallvet.fr -> tenant "clinique-martin").
    # When no sub-domain matches, the DEFAULT tenant below is used
    # (single-clinic deployment / local dev / tests).
    BASE_DOMAIN: str = "angeallvet.localhost"
    DEFAULT_TENANT_SLUG: str = "default"
    # Central stack serving several tenants by sub-domain: set True so an unknown
    # sub-domain is rejected (404) instead of silently falling back to the
    # default/central database. Single-clinic / dev / tests keep it False.
    MULTI_TENANT: bool = False
    # Optional Host allow-list (comma list) enforced by TrustedHostMiddleware in
    # production. Empty = disabled. e.g. "angeallvet.fr,*.angeallvet.fr".
    TRUSTED_HOSTS: str = ""

    # --- PocketBase (authentication provider) --------------------------
    # Each tenant runs its OWN PocketBase instance (tenant-local auth).
    # These values configure the DEFAULT tenant; additional tenants store
    # their own PocketBase URL + superuser credentials in the central
    # `tenants` table. The backend reaches PocketBase over the internal
    # Docker network (service name), never the public sub-domain.
    POCKETBASE_URL: str = "http://127.0.0.1:8090"
    POCKETBASE_ADMIN_EMAIL: str = ""
    POCKETBASE_ADMIN_PASSWORD: str = ""
    POCKETBASE_USERS_COLLECTION: str = "users"

    # --- Application JWT ------------------------------------------------
    # After verifying a PocketBase token, the backend issues its OWN JWT
    # signed with a PER-TENANT secret (derived from APP_SECRET_KEY + the
    # tenant slug, or overridden by the tenant's `auth_jwt_secret` column),
    # so a token minted for one tenant is rejected by another.
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12h

    # Platform (super-admin) token guarding the cross-tenant registry endpoints
    # (/auth/tenants*). MUST be set to use those endpoints; empty = disabled.
    # This is distinct from per-tenant ADMIN role so a clinic admin can never
    # read or manage other tenants.
    PLATFORM_ADMIN_TOKEN: str = ""

    # --- Paid modules (per-tenant entitlements) ------------------------
    # Modules (SMS, Invoice Ninja, Google Calendar…) are unlocked by a
    # cryptographically signed license (Ed25519). The app holds ONLY the public
    # key, so it can verify but never forge a license — editing this .env cannot
    # grant a module without the deployer's private key. See app/core/licensing.
    LICENSE_PUBLIC_KEY: str = ""   # PEM (escaped \n accepted). Safe to ship.
    LICENSE: str = ""              # the signed license token for THIS tenant.
    # Dev/test convenience: when NO public key is set in a dev environment, all
    # modules are enabled. Optionally restrict here (comma list). Ignored as soon
    # as a public key is configured, and always ignored in production.
    DEV_MODULES: str = ""
    # Maximum number of (active) users the admin can create, admin included.
    # 0 = unlimited. This is the plain-.env knob used when no public key is set;
    # in production the signed license's `max_users` claim takes over (so a
    # clinic can't lift its own seat cap by editing .env). See app/core/licensing.
    MAX_USERS: int = 0

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "AngeallVet"
    SMTP_FROM_EMAIL: str = ""
    SMTP_TLS: bool = True

    # SMS
    SMS_PROVIDER: str = "twilio"
    SMS_API_KEY: str = ""
    SMS_API_SECRET: str = ""
    SMS_FROM_NUMBER: str = ""

    # Background reminder scheduler. Disable on extra web workers to avoid
    # duplicate sends (only one process should run the scheduler).
    ENABLE_SCHEDULER: bool = True
    REMINDER_HOUR: int = 8  # local hour the daily reminder job runs

    # Google Calendar
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Files
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Security
    ENCRYPTION_KEY: str = ""
    DATA_RETENTION_YEARS: int = 5

    # Initial admin (created on first startup if no users exist)
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_FIRST_NAME: str = "Admin"
    INITIAL_ADMIN_LAST_NAME: str = "AngeallVet"

    # Demo
    DEMO_MODE: bool = False
    SEED_DEMO_DATA: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    @property
    def trusted_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def is_dev_env(self) -> bool:
        """True for development-like environments (dev/local/test)."""
        return self.APP_ENV.lower() in ("development", "dev", "local", "test")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
