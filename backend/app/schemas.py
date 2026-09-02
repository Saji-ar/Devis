"""Schemas Pydantic : contrats d'API + representation structuree d'un devis.

DevisData reflete EXACTEMENT le template : dates + tableau de produits (Produit, Quantite,
Prix Unit HT, TVA). Les infos client (nom, tel, source) vivent dans la base, pas sur la feuille.
"""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# ---------- Contenu structure d'un devis (edite dans le front) ----------

class LigneDevis(BaseModel):
    produit: str = ""
    quantite: float = 0.0
    prix_unit_ht: float = 0.0
    tva_pct: float = 10.0        # en % (10 = 10%) ; stocke en fraction (0.1) dans le xlsx

    @property
    def total_ht(self) -> float:
        return round(self.quantite * self.prix_unit_ht, 2)


class DevisData(BaseModel):
    date_devis: date = Field(default_factory=date.today)
    date_prestation: Optional[date] = None
    # Bloc client affiche a droite du devis (cellules E10-E12). Rempli par le backend
    # a partir du client rattache ; relu depuis la feuille lors d'un scan.
    client_nom: str = ""
    client_tel: str = ""
    client_email: str = ""
    lignes: list[LigneDevis] = Field(default_factory=list)

    def total_ht(self) -> float:
        return round(sum(l.total_ht for l in self.lignes), 2)

    def total_tva(self) -> float:
        return round(sum(l.total_ht * (l.tva_pct / 100) for l in self.lignes), 2)

    def total_ttc(self) -> float:
        return round(self.total_ht() + self.total_tva(), 2)


# ---------- Contrats d'API ----------

class ClientCreate(BaseModel):
    nom: str
    telephone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    nom: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class DevisCreate(BaseModel):
    client_id: int
    titre: Optional[str] = None
    reference: Optional[str] = None  # auto-genere si absent


class VersionCreate(BaseModel):
    """Cree une nouvelle version datee d'un devis a partir du contenu structure."""
    data: DevisData
    note: Optional[str] = None
