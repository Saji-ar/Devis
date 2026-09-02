"""Export PDF fidele a la mise en page Excel via LibreOffice headless.

LibreOffice (`soffice`) convertit le .xlsx en .pdf en conservant la mise en page
(polices, bordures, logo, zone d'impression). Fonctionne sur Raspberry Pi (ARM).
Installation Pi : sudo apt-get install libreoffice-calc
"""
import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_soffice() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    # Emplacements courants (macOS / Linux)
    for candidate in (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/opt/homebrew/bin/soffice",
    ):
        if Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "LibreOffice introuvable. Installez-le (Pi: sudo apt-get install libreoffice-calc)."
    )


def xlsx_to_pdf(xlsx_path: Path, out_dir: Path | None = None) -> Path:
    """Convertit un .xlsx en .pdf. Retourne le chemin du PDF genere."""
    soffice = _find_soffice()
    xlsx_path = Path(xlsx_path)
    out_dir = Path(out_dir) if out_dir else xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Profil utilisateur temporaire pour eviter les conflits d'instances concurrentes.
    with tempfile.TemporaryDirectory() as profile:
        result = subprocess.run(
            [
                soffice, "--headless", "--norestore",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to", "pdf", "--outdir", str(out_dir),
                str(xlsx_path),
            ],
            capture_output=True, text=True, timeout=120,
        )
    pdf_path = out_dir / (xlsx_path.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(
            f"Echec conversion PDF.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return pdf_path
