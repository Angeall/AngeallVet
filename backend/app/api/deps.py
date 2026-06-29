"""Shared FastAPI dependencies for authenticated, tenant-scoped endpoints.

The request's tenant is resolved by the sub-domain middleware (``app.main``)
and stashed on the ASGI ``scope``. ``get_tenant_db`` reads it back from
``request.scope`` and yields a session routed to that tenant's database, after
enforcing authentication via ``get_current_user``.
"""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import _session_for_scope
from app.core.security import get_current_user
from app.models.user import User


def get_tenant_db(
    request: Request,
    _current_user: User = Depends(get_current_user),
):
    """Yield a DB session routed to the current request's tenant database.

    ``get_current_user`` is listed as a dependency so authentication is always
    enforced before a tenant session is handed out.
    """
    db: Session = _session_for_scope(request)
    try:
        yield db
    finally:
        db.close()
