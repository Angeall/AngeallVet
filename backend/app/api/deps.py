"""Shared FastAPI dependencies for authenticated, tenant-scoped endpoints.

Key invariant: ``get_current_user`` **must** run before ``get_db`` so that
the per-request context variable ``_current_tenant_db_url`` is set.  Because
FastAPI resolves ``Depends`` in parameter-declaration order, declaring
``db = Depends(get_db)`` before ``current_user = Depends(get_current_user)``
results in ``get_db`` reading a *None* tenant URL and silently falling back to
the central database.

``get_tenant_db`` solves this by listing ``get_current_user`` as an explicit
sub-dependency so the tenant context is always established first.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_tenant_db_url, _get_tenant_session_factory, _default_session_factory
from app.core.security import get_current_user
from app.models.user import User


def get_tenant_db(
    _current_user: User = Depends(get_current_user),
):
    """Yield a DB session routed to the current user's tenant database.

    ``get_current_user`` is resolved first (setting the tenant context var),
    then we read the context var and create a session for the correct DB.
    """
    tenant_url = get_tenant_db_url()
    if tenant_url:
        factory = _get_tenant_session_factory(tenant_url)
    else:
        factory = _default_session_factory
    db = factory()
    try:
        yield db
    finally:
        db.close()
