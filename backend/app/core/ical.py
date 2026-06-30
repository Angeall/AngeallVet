"""Minimal RFC 5545 (iCalendar) generation — no external dependency.

Used by the ``google_calendar`` module: a vet's appointments are published as a
live ``.ics`` feed that Google Calendar (or any client) subscribes to by URL and
re-polls on its own. We only need a small, correct subset (VEVENTs in UTC), so we
hand-roll it rather than pull in a library.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


def _esc(text) -> str:
    """Escape a TEXT value per RFC 5545 (\\ ; , and newlines)."""
    return (
        str(text if text is not None else "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _utc(dt: datetime) -> str:
    """Format a datetime as a UTC iCal timestamp (e.g. 20260630T140000Z).

    Naive datetimes are assumed to already be UTC.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _fold(line: str) -> str:
    """Fold a content line to <=75 octets, continuation lines start with a space.

    Folds on UTF-8 byte boundaries so multi-byte characters are never split.
    """
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    pieces = []
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:  # don't split a code point
            cut -= 1
        pieces.append(raw[:cut].decode("utf-8"))
        raw = raw[cut:]
    pieces.append(raw.decode("utf-8"))
    return "\r\n ".join(pieces)


_STATUS = {"CONFIRMED", "TENTATIVE", "CANCELLED"}


@dataclass
class ICalEvent:
    uid: str
    start: datetime
    end: datetime
    summary: str
    description: str = ""
    location: str = ""
    status: str = "CONFIRMED"  # CONFIRMED | TENTATIVE | CANCELLED


def build_calendar(name: str, events, *, now: Optional[datetime] = None) -> str:
    """Render a VCALENDAR string from a list of :class:`ICalEvent`."""
    stamp = _utc(now or datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AngeallVet//Agenda//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(name)}",
        f"NAME:{_esc(name)}",
        # Hint clients (incl. Google) to re-poll roughly every 15 minutes.
        "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
        "X-PUBLISHED-TTL:PT15M",
    ]
    for ev in events:
        status = ev.status if ev.status in _STATUS else "CONFIRMED"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{_esc(ev.uid)}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_utc(ev.start)}",
            f"DTEND:{_utc(ev.end)}",
            f"SUMMARY:{_esc(ev.summary)}",
        ]
        if ev.description:
            lines.append(f"DESCRIPTION:{_esc(ev.description)}")
        if ev.location:
            lines.append(f"LOCATION:{_esc(ev.location)}")
        lines.append(f"STATUS:{status}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
