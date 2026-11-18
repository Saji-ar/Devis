"""Registres Excel : export des clients + suivi des factures.

- clients.xlsx : export tenu a jour des clients (Nom, Telephone, Email, Source, Notes).
- suivi_factures.xlsx : registre des factures (N°, Client, dates, montants, Paye, Devis).
  Le statut "Paye" est modifiable a la main dans cet Excel ; il est relu a l'actualisation.
"""
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

from .config import settings

_CLIENTS_HEADERS = ["Nom", "Téléphone", "Email", "Adresse", "CP / Ville", "Source", "Notes"]
_SUIVI_HEADERS = ["N°", "Client", "Date facture", "Échéance", "HT", "TVA", "TTC", "Payé", "Devis"]


def export_clients(clients) -> None:
    """Ecrit clients.xlsx a partir de la liste des clients."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    ws.append(_CLIENTS_HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for cl in clients:
        ws.append([cl.nom, cl.telephone or "", cl.email or "",
                   cl.adresse_1 or "", cl.adresse_2 or "", cl.source or "", cl.notes or ""])
    ws.column_dimensions["A"].width = 28
    for col in ("B", "C", "D", "E", "F", "G"):
        ws.column_dimensions[col].width = 22
    settings.clients_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(settings.clients_xlsx)


def _paye_to_bool(v) -> bool:
    return str(v).strip().lower() in ("oui", "1", "true", "vrai", "x", "paye", "payé")


def read_suivi_paye() -> dict:
    """Relit le statut Paye saisi a la main dans suivi_factures.xlsx : {numero: bool}."""
    path = settings.suivi_xlsx
    if not path.exists():
        return {}
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception:
        return {}
    ws = wb.active
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[0] in (None, ""):
            continue
        numero = str(row[0]).strip()
        paye = row[7] if len(row) > 7 else None
        out[numero] = _paye_to_bool(paye)
    return out


def write_suivi(rows: list[dict]) -> None:
    """Ecrit suivi_factures.xlsx. Chaque row : numero, client, date_facture, echeance,
    ht, tva, ttc, paye (bool), devis."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Suivi"
    ws.append(_SUIVI_HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in sorted(rows, key=lambda x: x["numero"]):
        ws.append([
            r["numero"], r.get("client", ""),
            r.get("date_facture", ""), r.get("echeance", ""),
            r.get("ht", 0), r.get("tva", 0), r.get("ttc", 0),
            "Oui" if r.get("paye") else "Non",
            r.get("devis", ""),
        ])
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 28
    for col in ("C", "D", "E", "F", "G", "H", "I"):
        ws.column_dimensions[col].width = 14
    settings.suivi_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(settings.suivi_xlsx)
