from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from gotrue.errors import AuthApiError
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.core.supabase import get_supabase_admin
from app.models.user import User, UserRole, RolePermission, Notification, DEFAULT_PERMISSIONS
from app.models.tenant import Tenant
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse,
    RolePermissionUpdate, RolePermissionResponse, NotificationResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user: creates Supabase auth account + local profile."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    supabase = get_supabase_admin()
    try:
        auth_response = supabase.auth.admin.create_user({
            "email": data.email,
            "password": data.password,
            "email_confirm": True,
            "user_metadata": {
                "first_name": data.first_name,
                "last_name": data.last_name,
                "role": data.role.value,
            },
        })
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=f"Erreur Supabase: {e.message}")

    user = User(
        supabase_uid=auth_response.user.id,
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
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate via Supabase and return tokens."""
    supabase = get_supabase_admin()
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    session = auth_response.session
    if not session:
        raise HTTPException(status_code=401, detail="Échec de l'authentification")

    user = db.query(User).filter(User.supabase_uid == auth_response.user.id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Profil utilisateur non trouvé. Contactez un administrateur.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh tokens via Supabase."""
    supabase = get_supabase_admin()
    try:
        auth_response = supabase.auth.refresh_session(refresh_token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Token de rafraîchissement invalide")

    session = auth_response.session
    if not session:
        raise HTTPException(status_code=401, detail="Échec du rafraîchissement")

    user = db.query(User).filter(User.supabase_uid == auth_response.user.id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(User).all()


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    update_data = data.model_dump(exclude_unset=True)

    # Sync email change to Supabase
    if "email" in update_data and update_data["email"] != user.email:
        supabase = get_supabase_admin()
        try:
            supabase.auth.admin.update_user_by_id(
                user.supabase_uid,
                {"email": update_data["email"]},
            )
        except AuthApiError as e:
            raise HTTPException(status_code=400, detail=f"Erreur Supabase: {e.message}")

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


# ─── Role Permissions ───────────────────────────────────────────────

@router.get("/permissions", response_model=list[RolePermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.get("/notifications/unread-count")
def unread_count(
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


# ─── Tenant Management ────────────────────────────────────────────

@router.get("/tenants")
def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """List all tenants (super-admin only)."""
    return db.query(Tenant).order_by(Tenant.name).all()


@router.post("/tenants", status_code=201)
def create_tenant(
    name: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Create a new tenant (clinic/organisation)."""
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        raise HTTPException(status_code=400, detail="Ce slug est deja utilise")
    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.put("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: int,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant non trouve")
    if name is not None:
        tenant.name = name
    if is_active is not None:
        tenant.is_active = is_active
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/tenants/{tenant_id}/assign-user")
def assign_user_to_tenant(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Assign a user to a tenant. Also updates Supabase app_metadata for RLS."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant non trouve")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouve")

    user.tenant_id = tenant_id
    db.commit()

    # Sync tenant_id to Supabase app_metadata so JWT includes it
    try:
        supabase = get_supabase_admin()
        supabase.auth.admin.update_user_by_id(
            user.supabase_uid,
            {"app_metadata": {"tenant_id": tenant_id}},
        )
    except Exception as e:
        # Non-blocking: the DB is the source of truth
        import logging
        logging.getLogger(__name__).warning("Failed to sync tenant_id to Supabase: %s", e)

    return {"ok": True, "user_id": user_id, "tenant_id": tenant_id}
