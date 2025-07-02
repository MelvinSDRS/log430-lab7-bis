#!/usr/bin/env python3
"""
Database configuration et modèles pour Customer Service
Base de données: customer_db (PostgreSQL)
"""

import os
import hashlib
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Configuration base de données
DATABASE_URL = os.getenv(
    'CUSTOMER_DB_URL', 
    'postgresql://customer_user:customer_password@customer-db:5432/customer_db'
)

Base = declarative_base()
engine = None
SessionLocal = None

# Modèles SQLAlchemy pour Customer Service
class CustomerModel(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    telephone = Column(String(20), nullable=True)
    date_naissance = Column(Date, nullable=True)
    actif = Column(Boolean, default=True, nullable=False)
    date_creation = Column(DateTime, default=datetime.utcnow)
    derniere_connexion = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    adresses = relationship("AddressModel", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self, include_sensitive=False):
        result = {
            'id': self.id,
            'email': self.email,
            'nom': self.nom,
            'prenom': self.prenom,
            'telephone': self.telephone,
            'date_naissance': self.date_naissance.isoformat() if self.date_naissance else None,
            'actif': self.actif,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'derniere_connexion': self.derniere_connexion.isoformat() if self.derniere_connexion else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            result['password_hash'] = self.password_hash
            
        return result

    @staticmethod
    def hash_password(password: str) -> str:
        """Hasher un mot de passe avec SHA-256 + salt"""
        salt = "customer-service-salt-2025"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Vérifier un mot de passe"""
        return self.password_hash == self.hash_password(password)


class AddressModel(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    type = Column(String(20), nullable=False)  # 'livraison', 'facturation'
    nom_complet = Column(String(200), nullable=False)
    adresse_ligne1 = Column(String(255), nullable=False)
    adresse_ligne2 = Column(String(255), nullable=True)
    ville = Column(String(100), nullable=False)
    province = Column(String(100), nullable=False)
    code_postal = Column(String(20), nullable=False)
    pays = Column(String(100), nullable=False, default='Canada')
    par_defaut = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    customer = relationship("CustomerModel", back_populates="adresses")

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'type': self.type,
            'nom_complet': self.nom_complet,
            'adresse_ligne1': self.adresse_ligne1,
            'adresse_ligne2': self.adresse_ligne2,
            'ville': self.ville,
            'province': self.province,
            'code_postal': self.code_postal,
            'pays': self.pays,
            'par_defaut': self.par_defaut,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def init_customer_db():
    """Initialiser la base de données Customer Service"""
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
    
    print("Customer Service Database initialisée")
    return get_customer_session()


def get_customer_session():
    """Obtenir une session de base de données"""
    if SessionLocal is None:
        init_customer_db()
    return SessionLocal()


def create_sample_customers(session):
    """Créer des clients d'exemple pour le développement"""
    
    sample_customers = [
        {
            'email': 'jean.dupont@email.com',
            'password': 'password123',
            'nom': 'Dupont',
            'prenom': 'Jean',
            'telephone': '514-555-1234',
            'date_naissance': datetime(1985, 3, 15).date()
        },
        {
            'email': 'marie.martin@email.com', 
            'password': 'password123',
            'nom': 'Martin',
            'prenom': 'Marie',
            'telephone': '438-555-5678',
            'date_naissance': datetime(1990, 7, 22).date()
        },
        {
            'email': 'pierre.tremblay@email.com',
            'password': 'password123',
            'nom': 'Tremblay',
            'prenom': 'Pierre',
            'telephone': '450-555-9876',
            'date_naissance': datetime(1988, 11, 8).date()
        }
    ]
    
    for customer_data in sample_customers:
        existing = session.query(CustomerModel).filter_by(email=customer_data['email']).first()
        if not existing:
            customer = CustomerModel(
                email=customer_data['email'],
                password_hash=CustomerModel.hash_password(customer_data['password']),
                nom=customer_data['nom'],
                prenom=customer_data['prenom'],
                telephone=customer_data['telephone'],
                date_naissance=customer_data['date_naissance']
            )
            session.add(customer)
    
    session.commit()
    print("Clients d'exemple créés")


def create_sample_addresses(session):
    """Créer des adresses d'exemple"""
    
    sample_addresses = [
        {
            'customer_id': 1,
            'type': 'livraison',
            'nom_complet': 'Jean Dupont',
            'adresse_ligne1': '123 Rue Sainte-Catherine',
            'ville': 'Montréal',
            'province': 'Québec',
            'code_postal': 'H3B 1A1',
            'pays': 'Canada',
            'par_defaut': True
        },
        {
            'customer_id': 2,
            'type': 'livraison',
            'nom_complet': 'Marie Martin',
            'adresse_ligne1': '456 Boulevard Saint-Laurent',
            'adresse_ligne2': 'Apt 3B',
            'ville': 'Montréal',
            'province': 'Québec',
            'code_postal': 'H2X 2T3',
            'pays': 'Canada',
            'par_defaut': True
        }
    ]
    
    for addr_data in sample_addresses:
        existing = session.query(AddressModel).filter_by(
            customer_id=addr_data['customer_id'],
            type=addr_data['type']
        ).first()
        if not existing:
            address = AddressModel(**addr_data)
            session.add(address)
    
    session.commit()
    print("Adresses d'exemple créées")


# Fonction utilitaire pour l'initialisation complète
def init_customer_service_db():
    """Initialisation complète du Customer Service avec données par défaut"""
    session = init_customer_db()
    try:
        create_sample_customers(session)
        create_sample_addresses(session)
    finally:
        session.close()
    
    return True


if __name__ == "__main__":
    init_customer_service_db()
    print("Customer Service Database initialisée avec succès") 