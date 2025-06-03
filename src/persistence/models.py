from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


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
    id_categorie = Column(Integer, ForeignKey('categories.id'), nullable=False)

    categorie = relationship("CategorieModel", back_populates="produits")
    lignes_vente = relationship("LigneVenteModel", back_populates="produit")


class CaisseModel(Base):
    __tablename__ = 'caisses'

    id = Column(Integer, primary_key=True)
    nom = Column(String(50), nullable=False)
    statut = Column(String(20), nullable=False, default='ACTIVE')

    ventes = relationship("VenteModel", back_populates="caisse")


class CaissierModel(Base):
    __tablename__ = 'caissiers'

    id = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)

    ventes = relationship("VenteModel", back_populates="caissier")


class VenteModel(Base):
    __tablename__ = 'ventes'

    id = Column(Integer, primary_key=True)
    horodatage = Column(DateTime, nullable=False, default=datetime.now)
    id_caisse = Column(Integer, ForeignKey('caisses.id'), nullable=False)
    id_caissier = Column(Integer, ForeignKey('caissiers.id'), nullable=False)
    statut = Column(String(20), nullable=False, default='COMPLETEE')

    caisse = relationship("CaisseModel", back_populates="ventes")
    caissier = relationship("CaissierModel", back_populates="ventes")
    lignes = relationship("LigneVenteModel", back_populates="vente")


class LigneVenteModel(Base):
    __tablename__ = 'lignes_vente'

    id = Column(Integer, primary_key=True)
    id_vente = Column(Integer, ForeignKey('ventes.id'), nullable=False)
    id_produit = Column(Integer, ForeignKey('produits.id'), nullable=False)
    qte = Column(Integer, nullable=False)

    vente = relationship("VenteModel", back_populates="lignes")
    produit = relationship("ProduitModel", back_populates="lignes_vente")
