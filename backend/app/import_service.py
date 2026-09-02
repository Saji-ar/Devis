"""Import d'anciens devis .xlsx (crees avant l'appli) vers la structure de l'appli.

Lit chaque .xlsx du dossier `import_source_dir`, le parse, et cree pour chacun un devis
+ une version v1 regeneree avec le template courant. Chaque ancien devis recoit son propre
client provisoire (a renommer ensuite dans l'appli). Idempotent : un devis deja importe
(meme reference) est ignore.
"""
import re
from pathlib import Path

from sqlmodel import Session, select

from .config import settings
from .models import Client, Devis, DevisVersion
from . import storage, excel_service


def _reference_from(stem: str) -> str:
    return re.sub(r"\s+", " ", stem).strip()


def import_old(session: Session) -> dict:
    src = settings.import_source_dir.strip()
    if not src:
        return {"imported": 0, "refs": [], "message": "import_source_dir non configure"}
    src_dir = Path(src)
    if not src_dir.is_dir():
        return {"imported": 0, "refs": [], "message": f"dossier introuvable: {src}"}

    template_name = settings.template_file.name
    imported, refs = 0, []

    for xlsx in sorted(src_dir.glob("*.xlsx")):
        # Ignore le template et les fichiers deja ranges dans la structure de l'appli.
        if xlsx.name == template_name or "template" in xlsx.name.lower():
            continue
        reference = _reference_from(xlsx.stem)
        if session.exec(select(Devis).where(Devis.reference == reference)).first():
            continue  # deja importe

        try:
            data = excel_service.read_devis(xlsx)
        except Exception:
            continue
        if not data.lignes:
            continue

        # Client provisoire propre a ce devis (a renommer dans l'appli).
        client_nom = f"A preciser — {reference}"
        client = session.exec(select(Client).where(Client.nom == client_nom)).first()
        if not client:
            client = Client(nom=client_nom)
            session.add(client); session.commit(); session.refresh(client)

        devis = Devis(reference=reference, client_id=client.id, titre="Importé")
        session.add(devis); session.commit(); session.refresh(devis)

        # Regenere une v1 propre avec le template courant (bloc client laisse vide).
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
        imported += 1
        refs.append(reference)

    return {"imported": imported, "refs": refs}
