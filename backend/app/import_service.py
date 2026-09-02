"""Import d'anciens devis .xlsx vers la structure de l'appli.

Deux entrees :
- `import_one` : importe UN fichier (utilise par l'upload depuis l'interface).
- `import_old` : importe tous les .xlsx d'un dossier (IMPORT_SOURCE_DIR), en boucle.

Chaque devis importe recoit son propre client provisoire "A preciser — <ref>", a renommer
ensuite dans l'appli. Idempotent : une reference deja presente est ignoree.
"""
from pathlib import Path

from sqlmodel import Session, select

from .config import settings
from .models import Client, Devis, DevisVersion
from . import storage, excel_service


def make_reference(stem: str) -> str:
    return storage.canonical_reference(stem)


def import_one(session: Session, src_path: Path, reference: str) -> str | None:
    """Importe un fichier .xlsx. Retourne la reference creee, ou None si ignore."""
    if session.exec(select(Devis).where(Devis.reference == reference)).first():
        return None  # deja importe
    try:
        data = excel_service.read_devis(src_path)
    except Exception:
        return None
    if not data.lignes:
        return None

    client_nom = f"A preciser — {reference}"
    client = session.exec(select(Client).where(Client.nom == client_nom)).first()
    if not client:
        client = Client(nom=client_nom)
        session.add(client); session.commit(); session.refresh(client)

    devis = Devis(reference=reference, client_id=client.id, titre="Importé")
    session.add(devis); session.commit(); session.refresh(devis)

    version_date = data.date_prestation or data.date_devis
    data.client_nom = data.client_tel = data.client_email = ""
    path = storage.version_path(reference, 1, version_date)
    excel_service.write_devis(data, path)

    session.add(DevisVersion(
        devis_id=devis.id, version_no=1, date_version=version_date,
        file_path=str(path), file_hash=storage.file_hash(path),
        montant_ht=data.total_ht(), montant_tva=data.total_tva(), montant_ttc=data.total_ttc(),
        data_json=data.model_dump_json(), origin="import",
    ))
    session.commit()
    return reference


def import_old(session: Session) -> dict:
    src = settings.import_source_dir.strip()
    if not src:
        return {"imported": 0, "refs": [], "message": "import_source_dir non configure"}
    src_dir = Path(src)
    if not src_dir.is_dir():
        return {"imported": 0, "refs": [], "message": f"dossier introuvable: {src}"}

    template_name = settings.template_file.name
    refs = []
    for xlsx in sorted(src_dir.glob("*.xlsx")):
        if xlsx.name == template_name or "template" in xlsx.name.lower():
            continue
        ref = import_one(session, xlsx, make_reference(xlsx.stem))
        if ref:
            refs.append(ref)
    return {"imported": len(refs), "refs": refs}
