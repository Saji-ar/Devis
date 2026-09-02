"""Convention de nommage et emplacement des fichiers devis.

  <DEVIS_DIR>/<reference>/v<N>_<AAAA-MM-JJ>.xlsx

Chaque devis = un dossier (nomme par sa reference). Chaque version = un fichier fige.
Cette convention est volontairement lisible pour qu'on puisse creer une version A LA MAIN
(copier le dernier fichier, incrementer N, changer la date) et que le scan la detecte.
"""
import hashlib
import re
from datetime import date
from pathlib import Path

from .config import settings

_VERSION_RE = re.compile(r"^v(\d+)_(\d{4}-\d{2}-\d{2})\.xlsx$", re.IGNORECASE)


def canonical_reference(s: str) -> str:
    """Reference "canonique" = nom de dossier. Garde lettres/chiffres/accents/espaces,
    remplace seulement les caracteres interdits en chemin. IDEMPOTENTE : appliquer deux
    fois donne le meme resultat, pour que reference == nom du dossier (evite les doublons au scan).
    """
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s or "devis"


def devis_folder(reference: str) -> Path:
    return settings.devis_dir / canonical_reference(reference)


def version_filename(version_no: int, d: date) -> str:
    return f"v{version_no}_{d.isoformat()}.xlsx"


def version_path(reference: str, version_no: int, d: date) -> Path:
    return devis_folder(reference) / version_filename(version_no, d)


def parse_version_filename(name: str):
    """Retourne (version_no, date) ou None si le nom ne suit pas la convention."""
    m = _VERSION_RE.match(name)
    if not m:
        return None
    return int(m.group(1)), date.fromisoformat(m.group(2))


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
