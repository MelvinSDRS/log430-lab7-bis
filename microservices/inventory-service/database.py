#!/usr/bin/env python3
"""
Database configuration pour Inventory Service
Base de données: inventory_db (PostgreSQL)
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Decimal, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Configuration base de données
DATABASE_URL = os.getenv(
    'INVENTORY_DB_URL', 
    'postgresql://inventory_user:inventory_password@inventory-db:5432/inventory_db'
)

Base = declarative_base()
engine = None
SessionLocal = None

# Modèles SQLAlchemy pour Inventory Service
class StockLocationModel(Base):
    __tablename__ = 'stock_locations'

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    type_location = Column(String(50), nullable=False)  # 'magasin', 'entrepot', 'depot'
    adresse = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    stocks = relationship("StockModel", back_populates="location")

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'type_location': self.type_location,
            'adresse': self.adresse,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StockModel(Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    location_id = Column(Integer, ForeignKey('stock_locations.id'), nullable=False)
    quantite_disponible = Column(Integer, default=0)
    quantite_reservee = Column(Integer, default=0)
    quantite_totale = Column(Integer, default=0)
    seuil_alerte = Column(Integer, default=10)
    prix_cout = Column(Decimal(10, 2), nullable=True)
    derniere_maj = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    location = relationship("StockLocationModel", back_populates="stocks")
    mouvements = relationship("StockMovementModel", back_populates="stock")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'location_id': self.location_id,
            'location_nom': self.location.nom if self.location else None,
            'quantite_disponible': self.quantite_disponible,
            'quantite_reservee': self.quantite_reservee,
            'quantite_totale': self.quantite_totale,
            'seuil_alerte': self.seuil_alerte,
            'prix_cout': float(self.prix_cout) if self.prix_cout else None,
            'en_alerte': self.quantite_disponible <= self.seuil_alerte,
            'derniere_maj': self.derniere_maj.isoformat() if self.derniere_maj else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class StockMovementModel(Base):
    __tablename__ = 'stock_movements'

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    type_mouvement = Column(String(50), nullable=False)  # 'entree', 'sortie', 'ajustement'
    quantite = Column(Integer, nullable=False)
    reference = Column(String(100), nullable=True)  # Référence commande/vente
    motif = Column(Text, nullable=True)
    utilisateur = Column(String(100), nullable=True)
    date_mouvement = Column(DateTime, default=datetime.utcnow)

    # Relations
    stock = relationship("StockModel", back_populates="mouvements")

    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'type_mouvement': self.type_mouvement,
            'quantite': self.quantite,
            'reference': self.reference,
            'motif': self.motif,
            'utilisateur': self.utilisateur,
            'date_mouvement': self.date_mouvement.isoformat() if self.date_mouvement else None
        }


def init_inventory_db():
    """Initialiser la base de données Inventory Service"""
    global engine, SessionLocal
    
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('SQL_ECHO', 'False').lower() == 'true',
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300
    )
    
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("Inventory Service Database initialisée")
    return get_inventory_session()


def get_inventory_session():
    """Obtenir une session de base de données"""
    if SessionLocal is None:
        init_inventory_db()
    return SessionLocal()


def create_sample_data(session):
    """Créer des données d'exemple"""
    
    # Locations de stock
    sample_locations = [
        {'nom': 'Magasin Centre-Ville', 'type_location': 'magasin', 'adresse': '123 Rue Sainte-Catherine, Montréal'},
        {'nom': 'Magasin Banlieue', 'type_location': 'magasin', 'adresse': '456 Boulevard des Sources, Dollard-des-Ormeaux'},
        {'nom': 'Entrepôt Principal', 'type_location': 'entrepot', 'adresse': '789 Rue Industrielle, Laval'}
    ]
    
    for loc_data in sample_locations:
        existing = session.query(StockLocationModel).filter_by(nom=loc_data['nom']).first()
        if not existing:
            location = StockLocationModel(**loc_data)
            session.add(location)
    
    session.commit()
    print("Locations de stock créées")


if __name__ == "__main__":
    session = init_inventory_db()
    create_sample_data(session)
    session.close()
    print("Inventory Service Database initialisée avec succès") 