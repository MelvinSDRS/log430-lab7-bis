from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class TypeEntite(Enum):
    MAGASIN = "MAGASIN"
    CENTRE_LOGISTIQUE = "CENTRE_LOGISTIQUE"
    MAISON_MERE = "MAISON_MERE"


class StatutDemande(Enum):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVEE = "APPROUVEE"
    REJETEE = "REJETEE"
    LIVREE = "LIVREE"


@dataclass
class Categorie:
    id: Optional[int]
    nom: str
    description: str


@dataclass
class Entite:
    """Représente une entité du système (magasin, centre logistique, maison mère)"""
    id: Optional[int]
    nom: str
    type_entite: TypeEntite
    adresse: str
    statut: str = "ACTIVE"


@dataclass
class Produit:
    id: Optional[int]
    nom: str
    prix: Decimal
    stock: int
    id_categorie: int
    seuil_alerte: int = 5
    description: Optional[str] = None
    categorie: Optional[Categorie] = None


@dataclass
class StockEntite:
    """Stock d'un produit dans une entité spécifique"""
    id: Optional[int]
    id_produit: int
    id_entite: int
    quantite: int
    seuil_alerte: int
    produit: Optional[Produit] = None
    entite: Optional[Entite] = None


@dataclass
class Caisse:
    id: Optional[int]
    nom: str
    statut: str
    id_entite: int
    entite: Optional[Entite] = None


@dataclass
class Caissier:
    id: Optional[int]
    nom: str
    id_entite: int
    entite: Optional[Entite] = None


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
    id_entite: int
    statut: str
    lignes: List[LigneVente]
    caisse: Optional[Caisse] = None
    caissier: Optional[Caissier] = None
    entite: Optional[Entite] = None

    @property
    def total(self) -> Decimal:
        return sum(ligne.sous_total for ligne in self.lignes)


@dataclass
class DemandeApprovisionnement:
    """Demande d'approvisionnement d'un magasin vers le centre logistique"""
    id: Optional[int]
    id_entite_demandeur: int
    id_entite_fournisseur: int
    id_produit: int
    quantite_demandee: int
    quantite_approuvee: Optional[int]
    statut: StatutDemande
    date_demande: datetime
    date_traitement: Optional[datetime]
    commentaire: Optional[str]
    
    # Relations
    entite_demandeur: Optional[Entite] = None
    entite_fournisseur: Optional[Entite] = None
    produit: Optional[Produit] = None


@dataclass
class TransfertStock:
    """Transfert de stock entre entités"""
    id: Optional[int]
    id_entite_source: int
    id_entite_destination: int
    id_produit: int
    quantite: int
    date_transfert: datetime
    id_demande_approvisionnement: Optional[int]
    
    # Relations
    entite_source: Optional[Entite] = None
    entite_destination: Optional[Entite] = None
    produit: Optional[Produit] = None
    demande: Optional[DemandeApprovisionnement] = None


@dataclass
class Rapport:
    """Rapport consolidé généré par le système"""
    id: Optional[int]
    titre: str
    type_rapport: str
    date_generation: datetime
    date_debut: datetime
    date_fin: datetime
    contenu_json: str
    genere_par: int  # ID du caissier/gestionnaire
    
    
@dataclass
class IndicateurPerformance:
    """Indicateur de performance pour tableau de bord"""
    entite_id: int
    entite_nom: str
    chiffre_affaires: Decimal
    nombre_ventes: int
    produits_en_rupture: int
    produits_en_surstock: int
    tendance_hebdomadaire: Decimal  # Pourcentage d'évolution
