"""Configuration de l'application, chargee depuis les variables d'environnement / .env."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: str = "../data"
    devis_subdir: str = "devis"
    template_path: str = "../data/templates/template.xlsx"
    database_url: str = "sqlite:///./devis.db"
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    # Dossier contenant d'anciens .xlsx a importer (bouton "Importer d'anciens devis").
    # Vide = fonction desactivee.
    import_source_dir: str = ""
    # Dossier ou sont ecrits les PDF exportes. Vide = <data_dir>/pdf.
    pdf_dir: str = ""

    @property
    def devis_dir(self) -> Path:
        return (Path(self.data_dir) / self.devis_subdir).resolve()

    @property
    def pdf_out_dir(self) -> Path:
        base = Path(self.pdf_dir) if self.pdf_dir else Path(self.data_dir) / "pdf"
        return base.resolve()

    @property
    def template_file(self) -> Path:
        return Path(self.template_path).resolve()

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# S'assure que les dossiers existent au demarrage.
settings.devis_dir.mkdir(parents=True, exist_ok=True)
settings.template_file.parent.mkdir(parents=True, exist_ok=True)
settings.pdf_out_dir.mkdir(parents=True, exist_ok=True)
