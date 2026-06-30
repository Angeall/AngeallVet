"""Google Calendar OAuth + REST client (httpx).

Thin wrapper over Google's OAuth2 token endpoint and Calendar API v3. The sync
engine (``app/core/google_sync.py``) drives it; this module just speaks HTTP so
it can be mocked in tests. All calls raise :class:`GoogleCalendarError` on
failure (except where a caller needs to special-case a status, e.g. 410 GONE on
an expired sync token).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
REVOKE_URI = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = ["https://www.googleapis.com/auth/calendar.events", "openid", "email"]
DEFAULT_TZ = "Europe/Brussels"


class GoogleCalendarError(Exception):
    pass


class SyncTokenExpired(GoogleCalendarError):
    """Google returned 410 GONE — the sync token is stale; do a full resync."""


# ─── OAuth ───────────────────────────────────────────────────────────────────

def build_auth_url(state: str) -> str:
    """Consent-screen URL (offline access so we get a refresh token)."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",  # force a refresh_token even on re-consent
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def _token_request(data: dict) -> dict:
    try:
        resp = httpx.post(TOKEN_URI, data=data, timeout=20)
    except httpx.HTTPError as exc:
        raise GoogleCalendarError(str(exc))
    if resp.status_code >= 400:
        raise GoogleCalendarError(f"OAuth {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for tokens."""
    return _token_request({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })


def refresh_access_token(refresh_token: str) -> dict:
    """Trade a refresh token for a fresh access token."""
    return _token_request({
        "refresh_token": refresh_token,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    })


def revoke(token: str) -> None:
    """Best-effort token revocation on disconnect."""
    try:
        httpx.post(REVOKE_URI, params={"token": token}, timeout=10)
    except httpx.HTTPError as exc:  # pragma: no cover - best effort
        logger.warning("Google token revoke failed: %s", exc)


def expiry_from(token_response: dict, *, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    # Refresh a minute early to avoid edge-of-expiry failures.
    return now + timedelta(seconds=int(token_response.get("expires_in", 3600)) - 60)


def email_from_id_token(id_token: str | None) -> str | None:
    """Read the email claim from Google's id_token (trusted: just fetched over TLS)."""
    if not id_token:
        return None
    try:
        import base64
        import json

        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("email")
    except Exception:  # pragma: no cover - defensive
        return None


# ─── Calendar REST client ────────────────────────────────────────────────────

class GoogleCalendarClient:
    def __init__(self, access_token: str, calendar_id: str = "primary"):
        self.access_token = access_token
        self.calendar_id = calendar_id

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{API_BASE}{path}"
        try:
            resp = httpx.request(method, url, headers=self._headers, timeout=30, **kwargs)
        except httpx.HTTPError as exc:
            raise GoogleCalendarError(str(exc))
        if resp.status_code == 410:
            raise SyncTokenExpired()
        if resp.status_code >= 400:
            raise GoogleCalendarError(f"Calendar {resp.status_code}: {resp.text[:200]}")
        return resp

    def list_events(self, *, sync_token: str | None = None, time_min: datetime | None = None):
        """Return ``(events, next_sync_token)`` across all pages.

        Uses the incremental ``syncToken`` when present; otherwise a full list
        from ``time_min``. Raises :class:`SyncTokenExpired` (410) when the token
        is stale — the caller should retry with no token.
        """
        events: list = []
        page_token = None
        next_sync_token = None
        while True:
            params = {"singleEvents": "true", "showDeleted": "true", "maxResults": 250}
            if page_token:
                params["pageToken"] = page_token
            elif sync_token:
                params["syncToken"] = sync_token
            elif time_min:
                params["timeMin"] = time_min.astimezone(timezone.utc).isoformat()
            data = self._request("GET", f"/calendars/{self.calendar_id}/events", params=params).json()
            events.extend(data.get("items", []))
            next_sync_token = data.get("nextSyncToken", next_sync_token)
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return events, next_sync_token

    def insert_event(self, payload: dict) -> dict:
        return self._request("POST", f"/calendars/{self.calendar_id}/events", json=payload).json()

    def update_event(self, event_id: str, payload: dict) -> dict:
        return self._request("PUT", f"/calendars/{self.calendar_id}/events/{event_id}", json=payload).json()

    def delete_event(self, event_id: str) -> None:
        try:
            self._request("DELETE", f"/calendars/{self.calendar_id}/events/{event_id}")
        except GoogleCalendarError as exc:
            # Already gone on Google's side is fine.
            if "404" not in str(exc) and "410" not in str(exc):
                raise

    def freebusy(self, start: datetime, end: datetime) -> list:
        payload = {
            "timeMin": start.astimezone(timezone.utc).isoformat(),
            "timeMax": end.astimezone(timezone.utc).isoformat(),
            "items": [{"id": self.calendar_id}],
        }
        data = self._request("POST", "/freeBusy", json=payload).json()
        cal = data.get("calendars", {}).get(self.calendar_id, {})
        return cal.get("busy", [])
