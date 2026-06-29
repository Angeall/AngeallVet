"""Idempotent-create support for the frontend's offline write queue.

When the browser is offline, a mutation is queued and replayed on reconnect.
If the original request actually reached the server but its response was lost,
a naive replay would create a duplicate (a second consultation, weight, …).
To prevent that, the client sends a stable ``Idempotency-Key`` header per
logical write; the endpoint records ``key -> created entity`` and, on replay,
returns the original entity.

The common case is a *sequential* replay (the queue resends after the first
response was lost), which these helpers fully cover. Concurrent duplicates are
backstopped by the primary-key uniqueness of ``idempotency_keys.key``.
"""

from typing import Optional

from fastapi import Header
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyKey


def idempotency_key_header(
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> Optional[str]:
    """FastAPI dependency exposing the optional ``Idempotency-Key`` header."""
    return idempotency_key or None


def replayed_entity_id(db: Session, key: Optional[str], entity_type: str) -> Optional[int]:
    """Return the id of the entity already created for ``key``, if any."""
    if not key:
        return None
    row = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == key, IdempotencyKey.entity_type == entity_type)
        .first()
    )
    return row.entity_id if row else None


def remember_entity(db: Session, key: Optional[str], entity_type: str, entity_id: int) -> None:
    """Record ``key -> entity`` within the caller's transaction.

    No-op when ``key`` is falsy. The caller commits (so the key and the created
    entity are persisted atomically).
    """
    if not key:
        return
    db.add(IdempotencyKey(key=key, entity_type=entity_type, entity_id=entity_id))
