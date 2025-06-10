from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class TypeEntiteEnum(enum.Enum):
    MAGASIN = "MAGASIN"
    CENTRE_LOGISTIQUE = "CENTRE_LOGISTIQUE"
    MAISON_MERE = "MAISON_MERE"


class StatutDemandeEnum(enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    APPROUVEE = "APPROUVEE"
    REJETEE = "REJETEE"
    LIVREE = "LIVREE"


class EntiteModel(Base):
    __tablename__ = 'entites'

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    type_entite = Column(SQLEnum(TypeEntiteEnum), nullable=False)
    adresse = Column(String(255), nullable=False)
    statut = Column(String(20), nullable=False, default='ACTIVE')

    # Relations
    caisses = relationship("CaisseModel", back_populates="entite")
    caissiers = relationship("CaissierModel", back_populates="entite")
    ventes = relationship("VenteModel", back_populates="entite")
    stocks = relationship("StockEntiteModel", back_populates="entite")
    demandes_emises = relationship("DemandeApprovisionnementModel", 
                                   foreign_keys="DemandeApprovisionnementModel.id_entite_demandeur",
                                   back_populates="entite_demandeur")
    demandes_recues = relationship("DemandeApprovisionnementModel",
                                   foreign_keys="DemandeApprovisionnementModel.id_entite_fournisseur", 
                                   back_populates="entite_fournisseur")


class CategorieModel(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    description = Column(String(255))

    produits = relationship("ProduitModel", back_populates="categorie")


class ProduitModel(Base):
    __tablename__ = 'produits'

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    prix = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    seuil_alerte = Column(Integer, nullable=False, default=5)
    id_categorie = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(String(500), nullable=True)

    categorie = relationship("CategorieModel", back_populates="produits")
    lignes_vente = relationship("LigneVenteModel", back_populates="produit")
    stocks_entites = relationship("StockEntiteModel", back_populates="produit")
    demandes = relationship("DemandeApprovisionnementModel", back_populates="produit")
    transferts_source = relationship("TransfertStockModel", 
                                     foreign_keys="TransfertStockModel.id_produit",
                                     back_populates="produit")


class StockEntiteModel(Base):
    __tablename__ = 'stocks_entites'

    id = Column(Integer, primary_key=True)
    id_produit = Column(Integer, ForeignKey('produits.id'), nullable=False)
    id_entite = Column(Integer, ForeignKey('entites.id'), nullable=False)
    quantite = Column(Integer, nullable=False, default=0)
    seuil_alerte = Column(Integer, nullable=False, default=5)

    produit = relationship("ProduitModel", back_populates="stocks_entites")
    entite = relationship("EntiteModel", back_populates="stocks")


class CaisseModel(Base):
    __tablename__ = 'caisses'

    id = Column(Integer, primary_key=True)
    nom = Column(String(50), nullable=False)
    statut = Column(String(20), nullable=False, default='ACTIVE')
    id_entite = Column(Integer, ForeignKey('entites.id'), nullable=False)

    entite = relationship("EntiteModel", back_populates="caisses")
    ventes = relationship("VenteModel", back_populates="caisse")


class CaissierModel(Base):
    __tablename__ = 'caissiers'

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    id_entite = Column(Integer, ForeignKey('entites.id'), nullable=False)

    entite = relationship("EntiteModel", back_populates="caissiers")
    ventes = relationship("VenteModel", back_populates="caissier")


class VenteModel(Base):
    __tablename__ = 'ventes'

    id = Column(Integer, primary_key=True)
    horodatage = Column(DateTime, nullable=False, default=datetime.now)
    id_caisse = Column(Integer, ForeignKey('caisses.id'), nullable=False)
    id_caissier = Column(Integer, ForeignKey('caissiers.id'), nullable=False)
    id_entite = Column(Integer, ForeignKey('entites.id'), nullable=False)
    statut = Column(String(20), nullable=False, default='COMPLETEE')

    caisse = relationship("CaisseModel", back_populates="ventes")
    caissier = relationship("CaissierModel", back_populates="ventes")
    entite = relationship("EntiteModel", back_populates="ventes")
    lignes = relationship("LigneVenteModel", back_populates="vente")


class LigneVenteModel(Base):
    __tablename__ = 'lignes_vente'

    id = Column(Integer, primary_key=True)
    id_vente = Column(Integer, ForeignKey('ventes.id'), nullable=False)
    id_produit = Column(Integer, ForeignKey('produits.id'), nullable=False)
    qte = Column(Integer, nullable=False)

    vente = relationship("VenteModel", back_populates="lignes")
    produit = relationship("ProduitModel", back_populates="lignes_vente")


class DemandeApprovisionnementModel(Base):
    __tablename__ = 'demandes_approvisionnement'

    id = Column(Integer, primary_key=True)
    id_entite_demandeur = Column(Integer, ForeignKey('entites.id'), nullable=False)
    id_entite_fournisseur = Column(Integer, ForeignKey('entites.id'), nullable=False)
    id_produit = Column(Integer, ForeignKey('produits.id'), nullable=False)
    quantite_demandee = Column(Integer, nullable=False)
    quantite_approuvee = Column(Integer, nullable=True)
    statut = Column(SQLEnum(StatutDemandeEnum), nullable=False, default=StatutDemandeEnum.EN_ATTENTE)
    date_demande = Column(DateTime, nullable=False, default=datetime.now)
    date_traitement = Column(DateTime, nullable=True)
    commentaire = Column(Text, nullable=True)

    entite_demandeur = relationship("EntiteModel", 
                                    foreign_keys=[id_entite_demandeur],
                                    back_populates="demandes_emises")
    entite_fournisseur = relationship("EntiteModel",
                                      foreign_keys=[id_entite_fournisseur], 
                                      back_populates="demandes_recues")
    produit = relationship("ProduitModel", back_populates="demandes")
    transferts = relationship("TransfertStockModel", back_populates="demande")


class TransfertStockModel(Base):
    __tablename__ = 'transferts_stock'

    id = Column(Integer, primary_key=True)
    id_entite_source = Column(Integer, ForeignKey('entites.id'), nullable=False)
    id_entite_destination = Column(Integer, ForeignKey('entites.id'), nullable=False)
    id_produit = Column(Integer, ForeignKey('produits.id'), nullable=False)
    quantite = Column(Integer, nullable=False)
    date_transfert = Column(DateTime, nullable=False, default=datetime.now)
    id_demande_approvisionnement = Column(Integer, 
                                          ForeignKey('demandes_approvisionnement.id'), 
                                          nullable=True)

    entite_source = relationship("EntiteModel", foreign_keys=[id_entite_source])
    entite_destination = relationship("EntiteModel", foreign_keys=[id_entite_destination])
    produit = relationship("ProduitModel", back_populates="transferts_source")
    demande = relationship("DemandeApprovisionnementModel", back_populates="transferts")


class RapportModel(Base):
    __tablename__ = 'rapports'

    id = Column(Integer, primary_key=True)
    titre = Column(String(200), nullable=False)
    type_rapport = Column(String(50), nullable=False)
    date_generation = Column(DateTime, nullable=False, default=datetime.now)
    date_debut = Column(DateTime, nullable=False)
    date_fin = Column(DateTime, nullable=False)
    contenu_json = Column(Text, nullable=False)
    genere_par = Column(Integer, ForeignKey('caissiers.id'), nullable=False)

    generateur = relationship("CaissierModel")

Index('idx_vente_entite_date', VenteModel.id_entite, VenteModel.horodatage)
Index('idx_stock_entite_produit', StockEntiteModel.id_entite, StockEntiteModel.id_produit)
Index('idx_produit_nom', ProduitModel.nom)
Index('idx_demande_statut', DemandeApprovisionnementModel.statut)
