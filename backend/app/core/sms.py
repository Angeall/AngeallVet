"""Real SMS sending. Currently supports Twilio (SMS_PROVIDER=twilio); other
providers raise a clear error so the channel fails loudly rather than silently."""

import httpx

from app.core.config import settings


class SmsError(Exception):
    pass


def is_configured() -> bool:
    return (settings.SMS_PROVIDER or "").lower() == "twilio" and bool(settings.SMS_API_KEY)


def send_sms(to, body, *, from_number=None):
    provider = (settings.SMS_PROVIDER or "").lower()
    if not to:
        raise SmsError("Destinataire manquant")
    sender = from_number or settings.SMS_FROM_NUMBER

    if provider == "twilio":
        if not settings.SMS_API_KEY or not settings.SMS_API_SECRET:
            raise SmsError("SMS Twilio non configuré")
        # SMS_API_KEY = Account SID, SMS_API_SECRET = Auth Token.
        sid = settings.SMS_API_KEY
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        try:
            resp = httpx.post(
                url,
                data={"To": to, "From": sender, "Body": body or ""},
                auth=(sid, settings.SMS_API_SECRET),
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise SmsError(str(exc))
        if resp.status_code >= 400:
            raise SmsError(f"Twilio {resp.status_code}: {resp.text[:200]}")
        return

    raise SmsError(f"Fournisseur SMS non supporté: {provider or '(vide)'}")
