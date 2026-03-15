from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.association import Association
from app.schemas.association import (
    AssociationCreate, AssociationUpdate, AssociationResponse,
)

router = APIRouter(prefix="/associations", tags=["Associations"])


@router.get("", response_model=list[AssociationResponse])
def list_associations(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Association).filter(Association.is_active == True).order_by(Association.name).all()


@router.post("", response_model=AssociationResponse, status_code=201)
def create_association(
    data: AssociationCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    assoc = Association(**data.model_dump())
    db.add(assoc)
    db.commit()
    db.refresh(assoc)
    return assoc


@router.get("/{association_id}", response_model=AssociationResponse)
def get_association(
    association_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    assoc = db.query(Association).filter(Association.id == association_id).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Association non trouvée")
    return assoc


@router.put("/{association_id}", response_model=AssociationResponse)
def update_association(
    association_id: int,
    data: AssociationUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    assoc = db.query(Association).filter(Association.id == association_id).first()
    if not assoc:
        raise HTTPException(status_code=404, detail="Association non trouvée")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assoc, field, value)

    db.commit()
    db.refresh(assoc)
    return assoc
