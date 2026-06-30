"""In-process daily scheduler that sends due reminders across all tenants.

Started from the FastAPI startup event (only when ENABLE_SCHEDULER is set and the
DB is not SQLite, i.e. not under tests). On multi-worker deployments, only one
worker should run it — set ENABLE_SCHEDULER=false on the others.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import _default_session_factory, _get_tenant_session_factory
from app.core.reminders import send_due_reminders

logger = logging.getLogger(__name__)
_scheduler = None


def run_all_tenants_reminders():
    from app.models.tenant import Tenant

    targets = [(_default_session_factory, settings.APP_URL)]  # default tenant (central DB)
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
                targets.append((_get_tenant_session_factory(tenant.database_url), base))
        finally:
            central.close()
    except Exception as exc:
        logger.warning("Reminder scheduler: could not list tenants: %s", exc)

    for factory, base in targets:
        db = factory()
        try:
            counts = send_due_reminders(db, base)
            if counts.get("sent") or counts.get("failed"):
                logger.info("Reminders (base=%s): %s", base, counts)
        except Exception as exc:
            logger.warning("Reminder run failed (base=%s): %s", base, exc)
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
    _scheduler.start()
    logger.info("Reminder scheduler started (daily at %02d:00)", settings.REMINDER_HOUR)
