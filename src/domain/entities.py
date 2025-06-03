from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Categorie:
    id: Optional[int]
    nom: str
    description: str


@dataclass
class Produit:
    id: Optional[int]
    nom: str
    prix: Decimal
    stock: int
    id_categorie: int
    categorie: Optional[Categorie] = None


@dataclass
class Caisse:
    id: Optional[int]
    nom: str
    statut: str


@dataclass
class Caissier:
    id: Optional[int]
    nom: str


@dataclass
class LigneVente:
    produit: Produit
    qte: int

    @property
    def sous_total(self) -> Decimal:
        return self.produit.prix * self.qte


@dataclass
class Vente:
    id: Optional[int]
    horodatage: datetime
    id_caisse: int
    id_caissier: int
    statut: str
    lignes: List[LigneVente]
    caisse: Optional[Caisse] = None
    caissier: Optional[Caissier] = None

    @property
    def total(self) -> Decimal:
        return sum(ligne.sous_total for ligne in self.lignes)
