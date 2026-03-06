from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from gotrue.errors import AuthApiError

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.core.supabase import get_supabase_admin
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse,
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
