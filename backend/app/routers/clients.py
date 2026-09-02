"""Routes CRUD pour les clients."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Client, Devis
from ..schemas import ClientCreate, ClientUpdate

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("")
def list_clients(session: Session = Depends(get_session)):
    return session.exec(select(Client).order_by(Client.nom)).all()


@router.post("")
def create_client(payload: ClientCreate, session: Session = Depends(get_session)):
    client = Client(**payload.model_dump())
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.get("/{client_id}")
def get_client(client_id: int, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    devis = session.exec(select(Devis).where(Devis.client_id == client_id)).all()
    return {"client": client, "devis": devis}


@router.patch("/{client_id}")
def update_client(client_id: int, payload: ClientUpdate, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    has_devis = session.exec(select(Devis).where(Devis.client_id == client_id)).first()
    if has_devis:
        raise HTTPException(400, "Impossible de supprimer : des devis sont rattaches a ce client.")
    session.delete(client)
    session.commit()
    return {"ok": True}
