from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_central_db, get_request_db, init_tenant_database
from app.core.security import get_current_user, require_roles, require_platform_admin, create_app_token
from app.core.tenancy import tenant_from_request
from app.core.licensing import resolve_modules, verify_license, ALL_MODULES
from app.core.pocketbase import (
    pb_auth_with_password,
    pb_verify_token,
    pb_admin_token,
    pb_create_user,
    pb_update_user,
)
from app.models.user import User, UserRole, RolePermission, Notification, DEFAULT_PERMISSIONS
from app.models.tenant import Tenant
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse, SessionRequest,
    RolePermissionUpdate, RolePermissionResponse, NotificationResponse, TenantResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─── Helpers ────────────────────────────────────────────────────────

def _link_or_get_user(db: Session, record: dict) -> Optional[User]:
    """Return the local profile for an authenticated PocketBase record.

    Looks up by PocketBase id first; on first login after a migration it links
    the profile by email (PocketBase has already verified the credentials).
    """
    pb_uid = record.get("id")
    email = (record.get("email") or "").lower()

    user = db.query(User).filter(User.pb_user_id == pb_uid).first()
    if user:
        return user
    # Migration relink by email — ONLY when PocketBase reports the email as
    # verified. A non-superuser cannot self-set verified=true, so this blocks
    # account takeover via public PocketBase sign-up with a victim's email.
    if email and record.get("verified") is True:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.pb_user_id = pb_uid
            db.commit()
            db.refresh(existing)
            return existing
    return None


def _issue_session(db: Session, request: Request, record: dict, pb_token: str) -> TokenResponse:
    """Build a TokenResponse (app JWT) for an authenticated PocketBase record."""
    user = _link_or_get_user(db, record)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Profil utilisateur non trouvé. Contactez un administrateur.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    tenant = tenant_from_request(request)
    app_token = create_app_token(record["id"], tenant.jwt_secret)
    return TokenResponse(
        access_token=app_token,
        refresh_token=pb_token,
        user=UserResponse.model_validate(user),
        modules=sorted(tenant.modules),
        max_users=tenant.max_users,
    )


# ─── Authentication ─────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    data: UserCreate,
    request: Request,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Create a new user: PocketBase auth record + local profile (admin only)."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    tenant = tenant_from_request(request)
    # Seat cap (from the subscription / signed license): refuse before any
    # side effect (no orphan PocketBase account) once the limit is reached.
    if tenant.max_users and db.query(User).filter(User.is_active == True).count() >= tenant.max_users:
        raise HTTPException(
            status_code=403,
            detail=f"Limite d'utilisateurs atteinte ({tenant.max_users}). "
                   "Mettez à niveau votre abonnement pour en ajouter.",
        )
    admin_token = pb_admin_token(tenant.pocketbase_url, tenant.pb_admin_email, tenant.pb_admin_password)
    record = pb_create_user(
        tenant.pocketbase_url,
        admin_token,
        email=data.email,
        password=data.password,
        name=f"{data.first_name} {data.last_name}".strip(),
    )

    user = User(
        pb_user_id=record["id"],
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_request_db),
):
    """Authenticate with email/password against the tenant's PocketBase.

    Convenience endpoint (e.g. CLI / tests). The SPA logs in against PocketBase
    directly and then calls ``/auth/session`` to exchange the PB token.
    """
    tenant = tenant_from_request(request)
    pb_token, record = pb_auth_with_password(tenant.pocketbase_url, data.email, data.password)
    return _issue_session(db, request, record, pb_token)


@router.post("/session", response_model=TokenResponse)
def create_session(
    data: SessionRequest,
    request: Request,
    db: Session = Depends(get_request_db),
):
    """Exchange a PocketBase token (from browser-side login) for an app JWT."""
    tenant = tenant_from_request(request)
    fresh_token, record = pb_verify_token(tenant.pocketbase_url, data.pb_token)
    return _issue_session(db, request, record, fresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/modules")
def get_modules(
    request: Request,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    """Paid modules + seat cap for the current tenant (UX hint; backend is the gate).

    Derived from the tenant's signed license — read-only and untrusted on the
    client side. ``available`` lists every module the product offers; ``max_users``
    is the seat cap (0 = unlimited) and ``user_count`` the current active users.
    """
    tenant = tenant_from_request(request)
    return {
        "modules": sorted(tenant.modules),
        "available": sorted(ALL_MODULES),
        "max_users": tenant.max_users,
        "user_count": db.query(User).filter(User.is_active == True).count(),
    }


@router.put("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    """Allow any authenticated user to update their own profile (limited fields)."""
    allowed = {"sidenav_color", "phone"}
    update_data = data.model_dump(exclude_unset=True)
    for field in list(update_data):
        if field not in allowed:
            del update_data[field]
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(User).all()


@router.get("/staff", response_model=list[UserResponse])
def list_staff(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    """List active staff (admins, vets, assistants). Available to all authenticated
    users so that vets/assistants can assign or reassign appointments."""
    return (
        db.query(User)
        .filter(
            User.is_active == True,
            User.role.in_([UserRole.ADMIN, UserRole.VETERINARIAN, UserRole.ASSISTANT]),
        )
        .order_by(User.last_name, User.first_name)
        .all()
    )


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    update_data = data.model_dump(exclude_unset=True)

    # PocketBase only owns the login identity (email). Names and roles live in
    # the application DB, so we only sync PocketBase when the email changes.
    if "email" in update_data and update_data["email"] != user.email:
        tenant = tenant_from_request(request)
        admin_token = pb_admin_token(tenant.pocketbase_url, tenant.pb_admin_email, tenant.pb_admin_password)
        pb_update_user(
            tenant.pocketbase_url, admin_token, user.pb_user_id,
            {"email": update_data["email"]},
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


# ─── Role Permissions ───────────────────────────────────────────────

@router.get("/permissions", response_model=list[RolePermissionResponse])
def list_permissions(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    """Get permissions for all roles. Returns DB-stored overrides or defaults."""
    result = []
    for role in UserRole:
        db_perm = db.query(RolePermission).filter(RolePermission.role == role).first()
        if db_perm:
            result.append(RolePermissionResponse(role=role.value, permissions=db_perm.permissions))
        else:
            result.append(RolePermissionResponse(
                role=role.value,
                permissions=DEFAULT_PERMISSIONS.get(role.value, {}),
            ))
    return result


@router.get("/permissions/me")
def my_permissions(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's permissions."""
    db_perm = db.query(RolePermission).filter(RolePermission.role == current_user.role).first()
    if db_perm:
        return {"role": current_user.role.value, "permissions": db_perm.permissions}
    return {
        "role": current_user.role.value,
        "permissions": DEFAULT_PERMISSIONS.get(current_user.role.value, {}),
    }


@router.put("/permissions/{role}", response_model=RolePermissionResponse)
def update_permissions(
    role: str,
    data: RolePermissionUpdate,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update permissions for a role (admin only)."""
    try:
        role_enum = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    db_perm = db.query(RolePermission).filter(RolePermission.role == role_enum).first()
    if db_perm:
        db_perm.permissions = data.permissions
    else:
        db_perm = RolePermission(role=role_enum, permissions=data.permissions)
        db.add(db_perm)

    db.commit()
    db.refresh(db_perm)
    return RolePermissionResponse(role=role_enum.value, permissions=db_perm.permissions)


# ─── Notifications ──────────────────────────────────────────────────

@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20),
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.get("/notifications/unread-count")
def unread_count(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).count()
    return {"count": count}


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    notif.is_read = True
    db.commit()
    return {"ok": True}


@router.patch("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_request_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


# ─── Tenant Management ────────────────────────────────────────────
# Tenants live in the CENTRAL registry database (not tenant DBs).
# We use get_central_db here explicitly.

def _with_modules(t: Tenant) -> Tenant:
    """Attach the decoded module list so TenantResponse can expose it."""
    t.modules = sorted(resolve_modules(t.slug, getattr(t, "license", "") or ""))
    return t


@router.get("/tenants", response_model=list[TenantResponse])
def list_tenants(
    db: Session = Depends(get_central_db),
    _: bool = Depends(require_platform_admin),
):
    """List all tenants (platform super-admin only)."""
    return [_with_modules(t) for t in db.query(Tenant).order_by(Tenant.name).all()]


@router.post("/tenants", status_code=201, response_model=TenantResponse)
def create_tenant(
    name: str,
    slug: str,
    database_url: str,
    subdomain: Optional[str] = None,
    pocketbase_url: Optional[str] = None,
    pb_admin_email: Optional[str] = None,
    pb_admin_password: Optional[str] = None,
    db: Session = Depends(get_central_db),
    _: bool = Depends(require_platform_admin),
):
    """Create a new tenant with its own database + PocketBase instance.

    The database_url should point to an existing (empty) PostgreSQL database.
    All tables will be automatically created in it. ``pocketbase_url`` is the
    internal URL of the tenant's PocketBase instance.
    """
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        raise HTTPException(status_code=400, detail="Ce slug est deja utilise")

    tenant = Tenant(
        name=name,
        slug=slug,
        database_url=database_url,
        subdomain=subdomain or slug,
        pocketbase_url=pocketbase_url,
        pb_admin_email=pb_admin_email,
        pb_admin_password=pb_admin_password,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Provision: create all data tables in the tenant's database
    try:
        init_tenant_database(database_url)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to provision tenant DB: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Tenant cree mais erreur de provisioning de la base: {e}",
        )

    return _with_modules(tenant)


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    subdomain: Optional[str] = None,
    pocketbase_url: Optional[str] = None,
    db: Session = Depends(get_central_db),
    _: bool = Depends(require_platform_admin),
):
    """Update a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant non trouve")
    if name is not None:
        tenant.name = name
    if is_active is not None:
        tenant.is_active = is_active
    if subdomain is not None:
        tenant.subdomain = subdomain
    if pocketbase_url is not None:
        tenant.pocketbase_url = pocketbase_url
    db.commit()
    db.refresh(tenant)
    return _with_modules(tenant)


@router.put("/tenants/{tenant_id}/license", response_model=TenantResponse)
def set_tenant_license(
    tenant_id: int,
    license: str = "",
    db: Session = Depends(get_central_db),
    _: bool = Depends(require_platform_admin),
):
    """Activate / update a tenant's paid modules by setting its signed license.

    Platform super-admin only — this is how the deployer turns modules on for a
    tenant in the central multi-tenant stack (a per-clinic stack uses the
    ``LICENSE`` env var instead). An empty string clears the license (free tier).
    The token is validated before being stored so a bad license can't be saved.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant non trouve")
    token = (license or "").strip()
    if token and not verify_license(token, expected_slug=tenant.slug):
        raise HTTPException(
            status_code=400,
            detail="Licence invalide (signature, expiration ou tenant non concordant).",
        )
    tenant.license = token or None
    db.commit()
    db.refresh(tenant)
    return _with_modules(tenant)


@router.post("/tenants/{tenant_id}/assign-user")
def assign_user_to_tenant(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_central_db),
    _: bool = Depends(require_platform_admin),
):
    """Assign a user to a tenant (registry-level bookkeeping)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant non trouve")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")

    user.tenant_id = tenant_id
    db.commit()

    return {"ok": True, "user_id": user_id, "tenant_id": tenant_id}
