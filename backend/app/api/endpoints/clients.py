from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.api.deps import get_tenant_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.client import Client, ClientAlert, ClientNote
from app.models.animal import Animal
from app.models.user import User
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientMergeRequest,
    ClientAlertCreate, ClientAlertResponse,
    ClientNoteCreate, ClientNoteResponse,
)

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("", response_model=list[ClientResponse])
def list_clients(
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Client).filter(Client.is_active == True, Client.merged_into_id == None)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Client.last_name.ilike(pattern),
                Client.first_name.ilike(pattern),
                Client.email.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.mobile.ilike(pattern),
            )
        )
    clients = query.order_by(Client.last_name).offset(skip).limit(limit).all()
    result = []
    for c in clients:
        resp = ClientResponse.model_validate(c)
        resp.animal_count = len(c.animals)
        result.append(resp)
    return result


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    resp = ClientResponse.model_validate(client)
    resp.animal_count = len(client.animals)
    return resp


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    client.is_active = False
    db.commit()


@router.post("/merge", response_model=ClientResponse)
def merge_clients(
    data: ClientMergeRequest,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    source = db.query(Client).filter(Client.id == data.source_client_id).first()
    target = db.query(Client).filter(Client.id == data.target_client_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    # Move all animals from source to target
    db.query(Animal).filter(Animal.client_id == source.id).update(
        {Animal.client_id: target.id}
    )
    # Transfer balance
    target.account_balance = (target.account_balance or 0) + (source.account_balance or 0)
    source.merged_into_id = target.id
    source.is_active = False

    db.commit()
    db.refresh(target)
    return target


# --- Client Alerts ---
@router.post("/{client_id}/alerts", response_model=ClientAlertResponse, status_code=201)
def add_client_alert(
    client_id: int,
    data: ClientAlertCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    alert = ClientAlert(client_id=client_id, **data.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{client_id}/alerts/{alert_id}", status_code=204)
def remove_client_alert(
    client_id: int,
    alert_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.query(ClientAlert).filter(
        ClientAlert.id == alert_id, ClientAlert.client_id == client_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    alert.is_active = False
    db.commit()


# --- Client Notes ---
def _enrich_note(note, db):
    """Add created_by_name to a client note."""
    data = ClientNoteResponse.model_validate(note).model_dump()
    user = db.query(User).filter(User.id == note.created_by_id).first()
    if user:
        data["created_by_name"] = f"{user.last_name} {user.first_name}"
    return data


@router.get("/{client_id}/notes", response_model=list[ClientNoteResponse])
def list_client_notes(
    client_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    notes = (
        db.query(ClientNote)
        .filter(ClientNote.client_id == client_id)
        .order_by(ClientNote.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_enrich_note(n, db) for n in notes]


@router.post("/{client_id}/notes", response_model=ClientNoteResponse, status_code=201)
def add_client_note(
    client_id: int,
    data: ClientNoteCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    note = ClientNote(client_id=client_id, content=data.content, source=data.source, created_by_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return _enrich_note(note, db)


@router.delete("/{client_id}/notes/{note_id}", status_code=204)
def delete_client_note(
    client_id: int,
    note_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(ClientNote).filter(
        ClientNote.id == note_id, ClientNote.client_id == client_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note non trouvée")
    db.delete(note)
    db.commit()
