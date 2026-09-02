"""Routes pour les devis, leurs versions, l'export PDF et le scan."""
import json
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import Client, Devis, DevisVersion
from ..schemas import DevisCreate, VersionCreate, DevisData
from .. import storage, excel_service, pdf_service, scan_service, import_service

router = APIRouter(prefix="/api/devis", tags=["devis"])


def _next_reference(session: Session) -> str:
    year = date.today().year
    count = len(session.exec(select(Devis).where(Devis.reference.like(f"{year}-%"))).all())
    return f"{year}-{count + 1:03d}"


@router.get("")
def list_devis(session: Session = Depends(get_session)):
    scan_service.maybe_scan(session)  # scan automatique (throttle)
    rows = session.exec(select(Devis).order_by(Devis.created_at.desc())).all()
    out = []
    for d in rows:
        versions = session.exec(
            select(DevisVersion).where(DevisVersion.devis_id == d.id)
            .order_by(DevisVersion.version_no.desc())
        ).all()
        client = session.get(Client, d.client_id)
        out.append({
            "devis": d,
            "client": client,
            "nb_versions": len(versions),
            "derniere_version": versions[0] if versions else None,
        })
    return out


@router.post("")
def create_devis(payload: DevisCreate, session: Session = Depends(get_session)):
    client = session.get(Client, payload.client_id)
    if not client:
        raise HTTPException(404, "Client introuvable")
    reference = payload.reference or _next_reference(session)
    devis = Devis(client_id=payload.client_id, titre=payload.titre, reference=reference)
    session.add(devis)
    session.commit()
    session.refresh(devis)
    return devis


@router.get("/{devis_id}")
def get_devis(devis_id: int, session: Session = Depends(get_session)):
    devis = session.get(Devis, devis_id)
    if not devis:
        raise HTTPException(404, "Devis introuvable")
    client = session.get(Client, devis.client_id)
    versions = session.exec(
        select(DevisVersion).where(DevisVersion.devis_id == devis_id)
        .order_by(DevisVersion.version_no.desc())
    ).all()
    return {"devis": devis, "client": client, "versions": versions}


@router.get("/version/{version_id}/data")
def get_version_data(version_id: int, session: Session = Depends(get_session)):
    v = session.get(DevisVersion, version_id)
    if not v:
        raise HTTPException(404, "Version introuvable")
    if v.data_json:
        return json.loads(v.data_json)
    # Repli : relire depuis le fichier
    return excel_service.read_devis(storage.Path(v.file_path)).model_dump()


@router.post("/{devis_id}/versions")
def create_version(devis_id: int, payload: VersionCreate, session: Session = Depends(get_session)):
    """Cree une nouvelle version datee : ecrit un nouveau .xlsx fige + ligne SQLite."""
    devis = session.get(Devis, devis_id)
    if not devis:
        raise HTTPException(404, "Devis introuvable")

    last = session.exec(
        select(DevisVersion).where(DevisVersion.devis_id == devis_id)
        .order_by(DevisVersion.version_no.desc())
    ).first()
    next_no = (last.version_no + 1) if last else 1

    data: DevisData = payload.data
    # Remplit le bloc client (E10-E12) depuis le client rattache au devis.
    client = session.get(Client, devis.client_id)
    if client:
        data.client_nom = client.nom or ""
        data.client_tel = client.telephone or ""
        data.client_email = client.email or ""

    path = storage.version_path(devis.reference, next_no, data.date_devis)
    excel_service.write_devis(data, path)

    version = DevisVersion(
        devis_id=devis_id,
        version_no=next_no,
        date_version=data.date_devis,
        file_path=str(path),
        file_hash=storage.file_hash(path),
        montant_ht=data.total_ht(),
        montant_tva=data.total_tva(),
        montant_ttc=data.total_ttc(),
        data_json=data.model_dump_json(),
        origin="app",
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.get("/version/{version_id}/xlsx")
def download_xlsx(version_id: int, session: Session = Depends(get_session)):
    v = session.get(DevisVersion, version_id)
    if not v:
        raise HTTPException(404, "Version introuvable")
    return FileResponse(v.file_path, filename=storage.Path(v.file_path).name)


@router.get("/version/{version_id}/pdf")
def download_pdf(version_id: int, session: Session = Depends(get_session)):
    v = session.get(DevisVersion, version_id)
    if not v:
        raise HTTPException(404, "Version introuvable")
    # PDF genere dans le dossier configurable (PDF_DIR, sinon <data_dir>/pdf).
    from ..config import settings
    pdf = pdf_service.xlsx_to_pdf(storage.Path(v.file_path), out_dir=settings.pdf_out_dir)
    return FileResponse(pdf, filename=pdf.name, media_type="application/pdf")


@router.post("/import")
async def import_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Importe un devis en deposant un fichier .xlsx (creation d'un devis + version v1)."""
    name = file.filename or "devis.xlsx"
    if not name.lower().endswith(".xlsx"):
        raise HTTPException(400, "Merci de déposer un fichier Excel .xlsx")
    contents = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        reference = import_service.make_reference(Path(name).stem)
        ref = import_service.import_one(session, tmp_path, reference)
    finally:
        tmp_path.unlink(missing_ok=True)
    if not ref:
        raise HTTPException(400, "Fichier non importé (déjà présent, vide, ou format non reconnu).")
    devis = session.exec(select(Devis).where(Devis.reference == ref)).first()
    return {"imported": 1, "reference": ref, "devis_id": devis.id if devis else None}
