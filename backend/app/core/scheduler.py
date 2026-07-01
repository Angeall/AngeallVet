"""In-process daily scheduler that sends due reminders across all tenants.

Started from the FastAPI startup event (only when ENABLE_SCHEDULER is set and the
DB is not SQLite, i.e. not under tests). On multi-worker deployments, only one
worker should run it — set ENABLE_SCHEDULER=false on the others.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import _default_session_factory, _get_tenant_session_factory
from app.core.licensing import MODULE_GOOGLE_CALENDAR, resolve_modules
from app.core.reminders import send_due_reminders, send_due_vaccination_reminders
from app.core.google_sync import sync_all_accounts

logger = logging.getLogger(__name__)
_scheduler = None

GOOGLE_SYNC_INTERVAL_MINUTES = 15


def _tenant_targets():
    """List ``(session_factory, base_url, modules)`` for every active tenant.

    The default tenant reads its license from the env; registry tenants from
    their row. Always includes the default tenant (central DB).
    """
    from app.models.tenant import Tenant

    default_modules = resolve_modules(settings.DEFAULT_TENANT_SLUG, settings.LICENSE)
    targets = [(_default_session_factory, settings.APP_URL, default_modules)]
    try:
        central = _default_session_factory()
        try:
            for tenant in central.query(Tenant).filter(Tenant.is_active == True).all():
                if not tenant.database_url:
                    continue
                base = settings.APP_URL
                sub = getattr(tenant, "subdomain", None)
                if sub:
                    base = f"https://{sub}.{settings.BASE_DOMAIN}"
                modules = resolve_modules(tenant.slug, getattr(tenant, "license", "") or "")
                targets.append((_get_tenant_session_factory(tenant.database_url), base, modules))
        finally:
            central.close()
    except Exception as exc:
        logger.warning("Scheduler: could not list tenants: %s", exc)
    return targets


def run_all_tenants_reminders():
    for factory, base, modules in _tenant_targets():
        db = factory()
        try:
            counts = send_due_reminders(db, base, modules=modules)
            if counts.get("sent") or counts.get("failed"):
                logger.info("Reminders (base=%s): %s", base, counts)
            vax = send_due_vaccination_reminders(db, base, modules=modules)
            if vax.get("sent") or vax.get("failed"):
                logger.info("Vaccination reminders (base=%s): %s", base, vax)
        except Exception as exc:
            logger.warning("Reminder run failed (base=%s): %s", base, exc)
        finally:
            db.close()


def run_all_tenants_google_sync():
    """Poll Google Calendar for every connected vet, in tenants that have the module."""
    for factory, base, modules in _tenant_targets():
        if MODULE_GOOGLE_CALENDAR not in modules:
            continue
        db = factory()
        try:
            totals = sync_all_accounts(db)
            if totals.get("users"):
                logger.info("Google sync (base=%s): %s", base, totals)
        except Exception as exc:
            logger.warning("Google sync failed (base=%s): %s", base, exc)
        finally:
            db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Europe/Brussels")
    _scheduler.add_job(
        run_all_tenants_reminders, "cron",
        hour=settings.REMINDER_HOUR, minute=0, id="daily_reminders",
    )
    _scheduler.add_job(
        run_all_tenants_google_sync, "interval",
        minutes=GOOGLE_SYNC_INTERVAL_MINUTES, id="google_calendar_sync",
    )
    _scheduler.start()
    logger.info(
        "Scheduler started (reminders daily at %02d:00, Google sync every %dmin)",
        settings.REMINDER_HOUR, GOOGLE_SYNC_INTERVAL_MINUTES,
    )
