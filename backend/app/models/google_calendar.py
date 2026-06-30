"""Two-way Google Calendar sync (the ``google_calendar`` module, OAuth path).

Three tables, all per-vet:
- ``GoogleCalendarAccount`` — the vet's OAuth connection. Refresh/access tokens
  are encrypted at rest (pgcrypto, like tenant secrets). ``sync_token`` drives
  Google's incremental delta pulls.
- ``ExternalCalendarEvent`` — events the vet owns on Google that we did NOT
  create; imported as read-only busy blocks so they show in the clinic agenda
  and feed double-booking detection.
- ``CalendarSyncConflict`` — a divergence needing human resolution. Sync policy
  is "signal, never overwrite", so anything ambiguous lands here instead of being
  auto-applied.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.crypto import EncryptedSecret


class GoogleCalendarAccount(Base):
    __tablename__ = "google_calendar_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    google_email = Column(String(255))
    calendar_id = Column(String(255), default="primary")
    # OAuth tokens — encrypted at rest (degrade to plaintext when ENCRYPTION_KEY
    # is unset, i.e. local dev / tests).
    refresh_token = Column(EncryptedSecret)
    access_token = Column(EncryptedSecret)
    token_expiry = Column(DateTime(timezone=True))
    # Google incremental sync token (opaque cursor for delta pulls).
    sync_token = Column(Text)
    last_sync_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExternalCalendarEvent(Base):
    __tablename__ = "external_calendar_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(20), default="google")
    external_id = Column(String(255), index=True)  # Google event id
    title = Column(String(500))
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True))
    all_day = Column(Boolean, default=False)
    status = Column(String(20), default="confirmed")  # confirmed | cancelled
    remote_updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarSyncConflict(Base):
    __tablename__ = "calendar_sync_conflicts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True, index=True)
    google_event_id = Column(String(255))
    # modified_on_google | deleted_on_google | double_booking
    conflict_type = Column(String(40), nullable=False)
    # Snapshot of both sides so the resolution UI can show what diverged.
    details = Column(JSON)
    status = Column(String(20), default="open", index=True)  # open | resolved
    resolution = Column(String(20))  # keep_app | keep_google | dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
