#!/usr/bin/env python3
"""
Database configuration et modèles pour Product Service
Base de données: product_db (PostgreSQL)
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# Configuration base de données
DATABASE_URL = os.getenv(
    'PRODUCT_DB_URL', 
    'postgresql://product_user:product_password@product-db:5432/product_db'
)

Base = declarative_base()
engine = None
SessionLocal = None

# Modèles SQLAlchemy pour Product Service
class CategoryModel(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    produits = relationship("ProductModel", back_populates="categorie")

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProductModel(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, index=True)
    prix = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    seuil_alerte = Column(Integer, nullable=False, default=5)
    id_categorie = Column(Integer, ForeignKey('categories.id'), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(50), unique=True, nullable=True, index=True)  # Stock Keeping Unit
    actif = Column(String(10), default='ACTIF')  # ACTIF, INACTIF, SUPPRIME
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    categorie = relationship("CategoryModel", back_populates="produits")

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'prix': float(self.prix),
            'stock': self.stock,
            'seuil_alerte': self.seuil_alerte,
            'id_categorie': self.id_categorie,
            'description': self.description,
            'sku': self.sku,
            'actif': self.actif,
            'categorie': self.categorie.to_dict() if self.categorie else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def init_product_db():
    """Initialiser la base de données Product Service"""
    global engine, SessionLocal
    
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('SQL_ECHO', 'False').lower() == 'true',
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300
    )
    
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    
    # Session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("Product Service Database initialisée")
    return get_product_session()


def get_product_session():
    """Obtenir une session de base de données"""
    if SessionLocal is None:
        init_product_db()
    return SessionLocal()


def create_default_categories(session):
    """Créer les catégories par défaut si elles n'existent pas"""
    
    default_categories = [
        {'nom': 'Électronique', 'description': 'Appareils électroniques et accessoires'},
        {'nom': 'Vêtements', 'description': 'Vêtements et accessoires de mode'},
        {'nom': 'Alimentation', 'description': 'Produits alimentaires et boissons'},
        {'nom': 'Maison & Jardin', 'description': 'Articles pour la maison et le jardin'},
        {'nom': 'Sport & Loisirs', 'description': 'Équipements sportifs et de loisirs'}
    ]
    
    for cat_data in default_categories:
        existing = session.query(CategoryModel).filter_by(nom=cat_data['nom']).first()
        if not existing:
            category = CategoryModel(
                nom=cat_data['nom'],
                description=cat_data['description']
            )
            session.add(category)
    
    session.commit()
    print("Catégories par défaut créées")


def create_sample_products(session):
    """Créer des produits d'exemple pour le développement"""
    
    sample_products = [
        {
            'nom': 'iPhone 16 Pro Max',
            'prix': 1299.99,
            'stock': 50,
            'seuil_alerte': 5,
            'id_categorie': 1,
            'description': 'Smartphone haut de gamme avec écran 6.7 pouces',
            'sku': 'IP16PM-256-BLK'
        },
        {
            'nom': 'MacBook Air M3',
            'prix': 1099.99,
            'stock': 25,
            'seuil_alerte': 3,
            'id_categorie': 1,
            'description': 'Ordinateur portable ultra-fin avec puce M3',
            'sku': 'MBA-M3-13-SLV'
        },
        {
            'nom': 'T-shirt Premium',
            'prix': 29.99,
            'stock': 100,
            'seuil_alerte': 20,
            'id_categorie': 2,
            'description': 'T-shirt en coton bio, coupe classique',
            'sku': 'TSH-PREM-M-BLU'
        }
    ]
    
    for prod_data in sample_products:
        existing = session.query(ProductModel).filter_by(sku=prod_data['sku']).first()
        if not existing:
            product = ProductModel(**prod_data)
            session.add(product)
    
    session.commit()
    print("Produits d'exemple créés")


# Fonction utilitaire pour l'initialisation complète
def init_product_service_db():
    """Initialisation complète du Product Service avec données par défaut"""
    session = init_product_db()
    try:
        create_default_categories(session)
        create_sample_products(session)
    finally:
        session.close()
    
    return True


if __name__ == "__main__":
    init_product_service_db()
    print("Product Service Database initialisée avec succès") 