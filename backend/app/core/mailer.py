"""Real e-mail sending over SMTP (configured via SMTP_* settings)."""

import smtplib
from email.message import EmailMessage

from app.core.config import settings


class MailerError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.SMTP_HOST)


def send_email(to, subject, body, *, from_email=None, from_name=None, reply_to=None, html=None):
    if not is_configured():
        raise MailerError("SMTP non configuré (SMTP_HOST)")
    if not to:
        raise MailerError("Destinataire manquant")

    sender_email = from_email or settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    sender_name = from_name or settings.SMTP_FROM_NAME

    msg = EmailMessage()
    msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    msg["To"] = to
    msg["Subject"] = subject or ""
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body or "")
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except MailerError:
        raise
    except Exception as exc:  # smtplib / socket errors
        raise MailerError(str(exc))
