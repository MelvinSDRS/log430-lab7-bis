#!/usr/bin/env python3
"""
Modèles de base de données pour Order Service
Pattern réutilisé de Customer Service pour cohérence
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

Base = declarative_base()

# Configuration identique au pattern Customer Service
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://postgres:postgres@localhost:5432/order_service_db'
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    """Créer une session de base de données"""
    return SessionLocal()


class OrderModel(Base):
    """Modèle pour les commandes e-commerce"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False, default='pending')  # pending, confirmed, shipped, delivered, cancelled
    total_amount = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    shipping_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Adresses
    shipping_address_json = Column(Text, nullable=False)  # JSON serialized address
    billing_address_json = Column(Text, nullable=True)    # JSON serialized address
    
    # Métadonnées
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    
    def to_dict(self, include_items: bool = True) -> Dict[str, Any]:
        """Convertir en dictionnaire - Pattern Customer Service"""
        result = {
            'id': self.id,
            'customer_id': self.customer_id,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'tax_amount': float(self.tax_amount),
            'shipping_amount': float(self.shipping_amount),
            'shipping_address_json': self.shipping_address_json,
            'billing_address_json': self.billing_address_json,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_items and self.items:
            result['items'] = [item.to_dict() for item in self.items]
        
        return result


class OrderItemModel(Base):
    """Modèle pour les articles de commande"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Métadonnées produit (snapshot au moment de la commande)
    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relations
    order = relationship("OrderModel", back_populates="items")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire - Pattern Customer Service"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'product_name': self.product_name,
            'product_description': self.product_description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def create_tables():
    """Créer les tables de la base de données"""
    Base.metadata.create_all(bind=engine)


def init_db():
    """Initialiser la base de données avec des données de test"""
    create_tables()
    
    session = get_session()
    try:
        # Vérifier si des données existent déjà
        existing_orders = session.query(OrderModel).first()
        if existing_orders:
            return
        
        # Données de test - même pattern que Customer Service
        sample_orders = [
            {
                'customer_id': 1,
                'status': 'delivered',
                'total_amount': 89.97,
                'tax_amount': 11.70,
                'shipping_amount': 9.99,
                'shipping_address_json': '{"nom_complet": "Jean Dupont", "adresse_ligne1": "123 Rue Principale", "ville": "Montréal", "province": "QC", "code_postal": "H1A 1A1", "pays": "Canada"}',
                'billing_address_json': '{"nom_complet": "Jean Dupont", "adresse_ligne1": "123 Rue Principale", "ville": "Montréal", "province": "QC", "code_postal": "H1A 1A1", "pays": "Canada"}'
            },
            {
                'customer_id': 2,
                'status': 'shipped',
                'total_amount': 156.48,
                'tax_amount': 20.34,
                'shipping_amount': 12.99,
                'shipping_address_json': '{"nom_complet": "Marie Martin", "adresse_ligne1": "456 Avenue des Pins", "ville": "Québec", "province": "QC", "code_postal": "G1R 2B2", "pays": "Canada"}',
                'billing_address_json': '{"nom_complet": "Marie Martin", "adresse_ligne1": "456 Avenue des Pins", "ville": "Québec", "province": "QC", "code_postal": "G1R 2B2", "pays": "Canada"}'
            }
        ]
        
        for order_data in sample_orders:
            order = OrderModel(**order_data)
            session.add(order)
            session.flush()  # Pour obtenir l'ID
            
            # Ajouter des items de test
            if order.id == 1:
                items = [
                    OrderItemModel(
                        order_id=order.id,
                        product_id=1,
                        quantity=2,
                        unit_price=29.99,
                        total_price=59.98,
                        product_name="Café Premium Bio",
                        product_description="Grains entiers 100% Arabica"
                    ),
                    OrderItemModel(
                        order_id=order.id,
                        product_id=3,
                        quantity=1,
                        unit_price=19.99,
                        total_price=19.99,
                        product_name="Thé Earl Grey",
                        product_description="Thé noir aux bergamotes"
                    )
                ]
            else:
                items = [
                    OrderItemModel(
                        order_id=order.id,
                        product_id=2,
                        quantity=3,
                        unit_price=15.99,
                        total_price=47.97,
                        product_name="Chocolat Noir 70%",
                        product_description="Tablette artisanale"
                    ),
                    OrderItemModel(
                        order_id=order.id,
                        product_id=4,
                        quantity=2,
                        unit_price=42.49,
                        total_price=84.98,
                        product_name="Miel de Lavande",
                        product_description="Pot 500g artisanal"
                    )
                ]
            
            for item in items:
                session.add(item)
        
        session.commit()
        print("Base de données Order Service initialisée avec succès")
        
    except Exception as e:
        session.rollback()
        print(f"Erreur lors de l'initialisation: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    init_db() 