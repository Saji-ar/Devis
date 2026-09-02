"""Modele de donnees SQLite (index/cache reconstruisible a partir des fichiers Excel).

Rappel d'architecture : les fichiers .xlsx sont la source de verite. SQLite ne fait
qu'indexer clients / devis / versions et mettre en cache le contenu structure (data_json)
pour pouvoir editer sans reparser a chaque fois. La table peut etre reconstruite par un scan.
"""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str = Field(index=True)
    telephone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None  # comment le client nous a connu
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    devis: list["Devis"] = Relationship(back_populates="client")


class Devis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id", index=True)
    reference: str = Field(index=True)          # code lisible, ex "2027-001"
    titre: Optional[str] = None
    statut: str = Field(default="brouillon")     # brouillon / envoye / accepte / refuse
    created_at: datetime = Field(default_factory=datetime.utcnow)

    client: Optional[Client] = Relationship(back_populates="devis")
    versions: list["DevisVersion"] = Relationship(
        back_populates="devis",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DevisVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    devis_id: int = Field(foreign_key="devis.id", index=True)
    version_no: int = Field(default=1)
    date_version: date = Field(default_factory=date.today)
    file_path: str                     # chemin du .xlsx (source de verite)
    file_hash: Optional[str] = None    # pour detecter les modifs manuelles
    montant_ht: float = 0.0
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    data_json: Optional[str] = None    # contenu structure mis en cache (JSON)
    origin: str = Field(default="app")  # "app" ou "manuel" (detecte au scan)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    devis: Optional[Devis] = Relationship(back_populates="versions")
