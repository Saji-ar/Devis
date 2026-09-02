"""Scan / reconciliation : le dossier Excel est la source de verite.

Parcourt <DEVIS_DIR>/<reference>/v<N>_<date>.xlsx et met a jour SQLite :
- cree les devis manquants (par reference = nom du dossier),
- cree/actualise les versions (detecte les fichiers ajoutes ou modifies a la main via le hash).

Le template ne contient pas d'infos client : un .xlsx cree a la main pour une reference
inconnue est rattache a un client "A preciser", a corriger ensuite dans l'appli.
"""
import time

from sqlmodel import Session, select

from .config import settings
from .models import Client, Devis, DevisVersion
from . import storage, excel_service

_CLIENT_A_PRECISER = "A preciser"

# Auto-scan throttle : on ne rescanne pas plus d'une fois toutes les N secondes.
_last_scan = 0.0
_SCAN_THROTTLE_S = 8.0


def _get_or_create_client(session: Session, nom: str) -> Client:
    nom = (nom or "").strip() or _CLIENT_A_PRECISER
    client = session.exec(select(Client).where(Client.nom == nom)).first()
    if not client:
        client = Client(nom=nom)
        session.add(client)
        session.commit()
        session.refresh(client)
    return client


def _get_or_create_devis(session: Session, reference: str, client_nom: str) -> Devis:
    devis = session.exec(select(Devis).where(Devis.reference == reference)).first()
    if not devis:
        client = _get_or_create_client(session, client_nom)
        devis = Devis(reference=reference, client_id=client.id)
        session.add(devis)
        session.commit()
        session.refresh(devis)
    return devis


def scan(session: Session) -> dict:
    """Reconcilie le dossier avec la base. Retourne un resume."""
    added, updated, skipped = 0, 0, 0

    for folder in sorted(p for p in settings.devis_dir.iterdir() if p.is_dir()):
        reference = folder.name
        for xlsx in sorted(folder.glob("*.xlsx")):
            parsed = storage.parse_version_filename(xlsx.name)
            if not parsed:
                skipped += 1
                continue
            version_no, d = parsed
            h = storage.file_hash(xlsx)

            existing = session.exec(
                select(DevisVersion).where(DevisVersion.file_path == str(xlsx))
            ).first()
            if existing and existing.file_hash == h:
                continue  # inchange

            data = excel_service.read_devis(xlsx)
            devis = _get_or_create_devis(session, reference, data.client_nom)

            if existing:
                existing.file_hash = h
                existing.date_version = d
                existing.version_no = version_no
                existing.montant_ht = data.total_ht()
                existing.montant_tva = data.total_tva()
                existing.montant_ttc = data.total_ttc()
                existing.data_json = data.model_dump_json()
                existing.origin = "manuel"
                session.add(existing)
                updated += 1
            else:
                session.add(DevisVersion(
                    devis_id=devis.id,
                    version_no=version_no,
                    date_version=d,
                    file_path=str(xlsx),
                    file_hash=h,
                    montant_ht=data.total_ht(),
                    montant_tva=data.total_tva(),
                    montant_ttc=data.total_ttc(),
                    data_json=data.model_dump_json(),
                    origin="manuel",
                ))
                added += 1
            session.commit()

    return {"added": added, "updated": updated, "skipped": skipped}


def maybe_scan(session: Session) -> None:
    """Scan automatique throttle : appele a chaque listing, silencieux en cas d'erreur."""
    global _last_scan
    now = time.time()
    if now - _last_scan < _SCAN_THROTTLE_S:
        return
    _last_scan = now
    try:
        scan(session)
    except Exception:
        pass
