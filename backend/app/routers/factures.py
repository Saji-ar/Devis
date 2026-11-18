"""Routes pour les factures (liste, edition, PDF, paye, import, actualisation)."""
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Client, Devis, Facture
from ..schemas import FactureCreate, FactureSave, FactureData
from ..config import settings
from .. import storage, excel_service, pdf_service, facture_service

router = APIRouter(prefix="/api/factures", tags=["factures"])


@router.get("")
def list_factures(session: Session = Depends(get_session)):
    facture_service.maybe_scan(session)
    rows = session.exec(select(Facture).order_by(Facture.numero.desc())).all()
    out = []
    for f in rows:
        client = session.get(Client, f.client_id)
        devis = session.get(Devis, f.devis_id) if f.devis_id else None
        out.append({"facture": f, "client": client,
                    "devis_reference": devis.reference if devis else None,
                    "has_pdf": bool(f.file_path) and storage.pdf_for(f.file_path).exists()})
    return out


@router.post("")
def create_facture(payload: FactureCreate, session: Session = Depends(get_session)):
    client = session.get(Client, payload.client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    numero = facture_service.next_numero(session)
    df = payload.date_facture or date.today()
    facture = Facture(
        numero=numero, client_id=payload.client_id,
        date_facture=df,
        date_echeance=payload.date_echeance or (df + timedelta(days=30)),
    )
    session.add(facture); session.commit(); session.refresh(facture)
    # Ecrit un fichier initial (vide de lignes) pour materialiser la facture.
    facture_service.save_facture(session, facture, FactureData(
        numero=numero, date_facture=facture.date_facture, date_echeance=facture.date_echeance,
        date_prestation=payload.date_prestation,
    ))
    return facture


@router.get("/{facture_id}")
def get_facture(facture_id: int, session: Session = Depends(get_session)):
    f = session.get(Facture, facture_id)
    if not f:
        raise HTTPException(404, "Facture introuvable")
    client = session.get(Client, f.client_id)
    devis = session.get(Devis, f.devis_id) if f.devis_id else None
    data = json.loads(f.data_json) if f.data_json else FactureData(numero=f.numero).model_dump(mode="json")
    return {"facture": f, "client": client, "devis_reference": devis.reference if devis else None,
            "data": data, "has_pdf": bool(f.file_path) and storage.pdf_for(f.file_path).exists()}


@router.put("/{facture_id}")
def save_facture(facture_id: int, payload: FactureSave, session: Session = Depends(get_session)):
    f = session.get(Facture, facture_id)
    if not f:
        raise HTTPException(404, "Facture introuvable")
    return facture_service.save_facture(session, f, payload.data)


class PayePayload(BaseModel):
    paye: bool


@router.post("/{facture_id}/paye")
def set_paye(facture_id: int, payload: PayePayload, session: Session = Depends(get_session)):
    f = session.get(Facture, facture_id)
    if not f:
        raise HTTPException(404, "Facture introuvable")
    f.statut_paye = payload.paye
    session.add(f); session.commit()
    facture_service.rebuild_suivi(session)   # repercute dans suivi_factures.xlsx
    session.refresh(f)
    return f


@router.post("/from-devis/{devis_id}")
def from_devis(devis_id: int, session: Session = Depends(get_session)):
    devis = session.get(Devis, devis_id)
    if not devis:
        raise HTTPException(404, "Devis introuvable")
    return facture_service.create_from_devis(session, devis)


@router.get("/{facture_id}/xlsx")
def download_xlsx(facture_id: int, session: Session = Depends(get_session)):
    f = session.get(Facture, facture_id)
    if not f or not f.file_path:
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(f.file_path, filename=f"Facture_{f.numero}.xlsx")


@router.get("/{facture_id}/pdf")
def download_pdf(facture_id: int, session: Session = Depends(get_session)):
    f = session.get(Facture, facture_id)
    if not f or not f.file_path:
        raise HTTPException(404, "Fichier introuvable")
    # Sert le PDF sauvegarde a cote du .xlsx ; le (re)genere s'il manque.
    pdf = storage.pdf_for(f.file_path)
    if not pdf.exists():
        pdf = pdf_service.xlsx_to_pdf(storage.Path(f.file_path), out_dir=pdf.parent)
    return FileResponse(pdf, filename=f"Facture_{f.numero}.pdf", media_type="application/pdf")


@router.post("/scan")
def run_scan(session: Session = Depends(get_session)):
    return facture_service.scan_factures(session)


@router.post("/import")
async def import_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Importe une facture en deposant un .xlsx (nomme AAAANN.xlsx de preference)."""
    name = file.filename or "facture.xlsx"
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(400, "Merci de déposer un fichier Excel .xlsx")
    numero = storage.parse_facture_filename(name) or facture_service.next_numero(session)
    contents = await file.read()
    dest = storage.facture_path(numero)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(contents)
    facture_service.scan_factures(session)
    f = session.exec(select(Facture).where(Facture.numero == numero)).first()
    return {"imported": 1, "numero": numero, "facture_id": f.id if f else None}
