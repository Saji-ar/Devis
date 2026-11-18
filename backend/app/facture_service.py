"""Logique metier des factures : numerotation, ecriture du fichier, scan, suivi.

- 1 fichier par facture : DATA_DIR/factures/AAAANN.xlsx (dossier plat).
- Numero AAAANN sequentiel, repart a 01 chaque annee.
- suivi_factures.xlsx regenere depuis la base ; le statut "Paye" y est relu (modifiable
  a la main) puis reapplique -> "fusion au scan".
"""
import json
import time
from datetime import date, timedelta

from sqlmodel import Session, select

from .config import settings
from .models import Client, Devis, DevisVersion, Facture
from .schemas import FactureData, LigneDevis
from . import storage, excel_service, registers

_ECHEANCE_JOURS = 30
_last_scan = 0.0
_SCAN_THROTTLE_S = 8.0


# ---------- Clients (cache partage) ----------

def get_or_create_client(session: Session, nom: str, adresse_1: str = "", adresse_2: str = "") -> Client:
    nom = (nom or "").strip() or "A preciser"
    client = session.exec(select(Client).where(Client.nom == nom)).first()
    if not client:
        client = Client(nom=nom, adresse_1=adresse_1 or None, adresse_2=adresse_2 or None)
        session.add(client); session.commit(); session.refresh(client)
    elif (adresse_1 or adresse_2) and not (client.adresse_1 or client.adresse_2):
        # Complete l'adresse si le client n'en avait pas (reconstruction depuis les factures).
        client.adresse_1 = adresse_1 or None
        client.adresse_2 = adresse_2 or None
        session.add(client); session.commit(); session.refresh(client)
    return client


# ---------- Numerotation ----------

def next_numero(session: Session) -> str:
    year = str(date.today().year)
    nums = []
    for f in session.exec(select(Facture).where(Facture.numero.like(f"{year}%"))).all():
        suf = f.numero[len(year):]
        if suf.isdigit():
            nums.append(int(suf))
    seq = (max(nums) + 1) if nums else 1
    return f"{year}{seq:03d}"        # AAAANNN, ex. 2026001


# ---------- Ecriture d'une facture ----------

def save_facture(session: Session, facture: Facture, data: FactureData) -> Facture:
    """Ecrit (ou remplace) le fichier .xlsx de la facture et met a jour la base + le suivi."""
    data.numero = facture.numero
    client = session.get(Client, facture.client_id)
    if client:
        data.client_nom = client.nom or ""
        data.client_tel = client.telephone or ""
        data.client_email = client.email or ""
        data.client_adresse_1 = client.adresse_1 or ""
        data.client_adresse_2 = client.adresse_2 or ""

    path = storage.facture_path(facture.numero)
    excel_service.write_facture(data, path)

    facture.file_path = str(path)
    facture.file_hash = storage.file_hash(path)
    facture.date_facture = data.date_facture
    facture.date_echeance = data.date_echeance
    facture.montant_ht = data.total_ht()
    facture.montant_tva = data.total_tva()
    facture.montant_ttc = data.total_ttc()
    facture.data_json = data.model_dump_json()
    session.add(facture); session.commit()
    rebuild_suivi(session)          # commits internes -> on rafraichit apres
    session.refresh(facture)
    return facture


def create_from_devis(session: Session, devis: Devis) -> Facture:
    """Cree une facture a partir du dernier etat d'un devis et marque le devis 'facture'."""
    last = session.exec(
        select(DevisVersion).where(DevisVersion.devis_id == devis.id)
        .order_by(DevisVersion.version_no.desc())
    ).first()
    lignes = []
    date_prestation = None
    if last and last.data_json:
        d = json.loads(last.data_json)
        lignes = [LigneDevis(**l) for l in d.get("lignes", [])]
        date_prestation = d.get("date_prestation")

    numero = next_numero(session)
    facture = Facture(
        numero=numero, client_id=devis.client_id, devis_id=devis.id, origin="devis",
        date_facture=date.today(), date_echeance=date.today() + timedelta(days=_ECHEANCE_JOURS),
    )
    session.add(facture); session.commit(); session.refresh(facture)

    fdata = FactureData(
        numero=numero, date_facture=facture.date_facture, date_echeance=facture.date_echeance,
        date_prestation=date.fromisoformat(date_prestation) if date_prestation else None,
        lignes=lignes,
    )
    save_facture(session, facture, fdata)

    devis.statut = "facturé"
    session.add(devis); session.commit()
    session.refresh(facture)   # le commit ci-dessus a expire l'objet
    return facture


# ---------- Suivi (registre Excel) ----------

def apply_suivi_paye(session: Session) -> None:
    """Actualisation : lit le statut 'Paye' saisi a la main dans l'Excel et l'applique en base."""
    paye_manuel = registers.read_suivi_paye()
    for f in session.exec(select(Facture)).all():
        if f.numero in paye_manuel and f.statut_paye != paye_manuel[f.numero]:
            f.statut_paye = paye_manuel[f.numero]
            session.add(f)
    session.commit()


def rebuild_suivi(session: Session) -> None:
    """Reecrit suivi_factures.xlsx depuis la base (sans relire le Paye : l'appli fait foi ici)."""
    rows = []
    for f in session.exec(select(Facture)).all():
        client = session.get(Client, f.client_id)
        devis = session.get(Devis, f.devis_id) if f.devis_id else None
        rows.append({
            "numero": f.numero, "client": client.nom if client else "",
            "date_facture": f.date_facture.isoformat() if f.date_facture else "",
            "echeance": f.date_echeance.isoformat() if f.date_echeance else "",
            "ht": f.montant_ht, "tva": f.montant_tva, "ttc": f.montant_ttc,
            "paye": f.statut_paye, "devis": devis.reference if devis else "",
        })
    registers.write_suivi(rows)


# ---------- Scan (actualisation) ----------

def scan_factures(session: Session) -> dict:
    added, updated, skipped = 0, 0, 0
    for xlsx in sorted(settings.factures_dir.glob("*.xlsx")):
        numero = storage.parse_facture_filename(xlsx.name)
        if not numero:
            skipped += 1
            continue
        h = storage.file_hash(xlsx)
        existing = session.exec(select(Facture).where(Facture.numero == numero)).first()
        if existing and existing.file_hash == h:
            continue
        data = excel_service.read_facture(xlsx)
        client = get_or_create_client(session, data.client_nom, data.client_adresse_1, data.client_adresse_2)
        if existing:
            existing.file_hash = h
            existing.date_facture = data.date_facture
            existing.date_echeance = data.date_echeance
            existing.montant_ht = data.total_ht()
            existing.montant_tva = data.total_tva()
            existing.montant_ttc = data.total_ttc()
            existing.data_json = data.model_dump_json()
            existing.origin = "manuel"
            session.add(existing); updated += 1
        else:
            session.add(Facture(
                numero=numero, client_id=client.id, origin="manuel",
                date_facture=data.date_facture, date_echeance=data.date_echeance,
                file_path=str(xlsx), file_hash=h,
                montant_ht=data.total_ht(), montant_tva=data.total_tva(), montant_ttc=data.total_ttc(),
                data_json=data.model_dump_json(),
            ))
            added += 1
        session.commit()
    apply_suivi_paye(session)   # recupere le "Paye" edite a la main dans l'Excel
    rebuild_suivi(session)
    return {"added": added, "updated": updated, "skipped": skipped}


def maybe_scan(session: Session) -> None:
    global _last_scan
    now = time.time()
    if now - _last_scan < _SCAN_THROTTLE_S:
        return
    _last_scan = now
    try:
        scan_factures(session)
    except Exception:
        pass
