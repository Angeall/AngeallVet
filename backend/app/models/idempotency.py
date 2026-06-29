from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class IdempotencyKey(Base):
    """Client-supplied idempotency keys, scoped to the tenant database.

    A write replayed from the frontend's offline queue carries the same
    ``Idempotency-Key`` header as its first attempt. We record
    ``key -> created entity`` so a replay returns the original result instead of
    creating a duplicate — essential here because primary keys are
    server-assigned integers (a naive replay would create a second record).
    """

    __tablename__ = "idempotency_keys"

    key = Column(String(64), primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
