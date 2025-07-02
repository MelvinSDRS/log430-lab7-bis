#!/usr/bin/env python3
"""
Services métier pour Product Service
Logique métier extraite de l'architecture monolithique
"""

from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from datetime import datetime

from database import ProductModel, CategoryModel


class ProductService:
    """Service métier pour la gestion des produits"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_products_paginated(self, page: int = 1, per_page: int = 20, search: str = '') -> List[Dict]:
        """Récupérer les produits avec pagination et recherche"""
        query = self.session.query(ProductModel).filter(ProductModel.actif == 'ACTIF')
        
        # Filtrage par recherche
        if search:
            search_filter = or_(
                ProductModel.nom.ilike(f'%{search}%'),
                ProductModel.description.ilike(f'%{search}%'),
                ProductModel.sku.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Pagination
        offset = (page - 1) * per_page
        products = query.offset(offset).limit(per_page).all()
        
        return [product.to_dict() for product in products]
    
    def count_products(self, search: str = '') -> int:
        """Compter le nombre total de produits"""
        query = self.session.query(ProductModel).filter(ProductModel.actif == 'ACTIF')
        
        if search:
            search_filter = or_(
                ProductModel.nom.ilike(f'%{search}%'),
                ProductModel.description.ilike(f'%{search}%'),
                ProductModel.sku.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        return query.count()
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Récupérer un produit par son ID"""
        product = self.session.query(ProductModel).filter(
            and_(ProductModel.id == product_id, ProductModel.actif == 'ACTIF')
        ).first()
        
        return product.to_dict() if product else None
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        """Récupérer un produit par son SKU"""
        product = self.session.query(ProductModel).filter(
            and_(ProductModel.sku == sku, ProductModel.actif == 'ACTIF')
        ).first()
        
        return product.to_dict() if product else None
    
    def create_product(self, product_data: Dict) -> Dict:
        """Créer un nouveau produit"""
        
        # Validation des données
        required_fields = ['nom', 'prix', 'id_categorie']
        for field in required_fields:
            if field not in product_data:
                raise ValueError(f"Le champ '{field}' est requis")
        
        # Vérifier que la catégorie existe
        category = self.session.query(CategoryModel).filter(
            CategoryModel.id == product_data['id_categorie']
        ).first()
        if not category:
            raise ValueError(f"Catégorie {product_data['id_categorie']} introuvable")
        
        # Validation prix
        if product_data['prix'] <= 0:
            raise ValueError("Le prix doit être supérieur à zéro")
        
        # Génération automatique du SKU si non fourni
        if 'sku' not in product_data or not product_data['sku']:
            product_data['sku'] = self._generate_sku(product_data['nom'])
        
        # Vérifier l'unicité du SKU
        if self._sku_exists(product_data['sku']):
            raise ValueError(f"Le SKU '{product_data['sku']}' existe déjà")
        
        # Créer le produit
        product = ProductModel(
            nom=product_data['nom'],
            prix=product_data['prix'],
            stock=product_data.get('stock', 0),
            seuil_alerte=product_data.get('seuil_alerte', 5),
            id_categorie=product_data['id_categorie'],
            description=product_data.get('description'),
            sku=product_data['sku']
        )
        
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        
        return product.to_dict()
    
    def update_product(self, product_id: int, update_data: Dict) -> Optional[Dict]:
        """Mettre à jour un produit"""
        product = self.session.query(ProductModel).filter(
            and_(ProductModel.id == product_id, ProductModel.actif == 'ACTIF')
        ).first()
        
        if not product:
            return None
        
        # Champs autorisés à la mise à jour
        allowed_fields = ['nom', 'prix', 'stock', 'seuil_alerte', 'description', 'sku']
        
        for field, value in update_data.items():
            if field in allowed_fields:
                if field == 'prix' and value <= 0:
                    raise ValueError("Le prix doit être supérieur à zéro")
                
                if field == 'sku' and value != product.sku:
                    if self._sku_exists(value):
                        raise ValueError(f"Le SKU '{value}' existe déjà")
                
                setattr(product, field, value)
        
        product.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(product)
        
        return product.to_dict()
    
    def delete_product(self, product_id: int) -> bool:
        """Supprimer un produit (soft delete)"""
        product = self.session.query(ProductModel).filter(
            and_(ProductModel.id == product_id, ProductModel.actif == 'ACTIF')
        ).first()
        
        if not product:
            return False
        
        # Soft delete
        product.actif = 'SUPPRIME'
        product.updated_at = datetime.utcnow()
        
        self.session.commit()
        return True
    
    def get_products_by_category(self, category_id: int) -> List[Dict]:
        """Récupérer tous les produits d'une catégorie"""
        products = self.session.query(ProductModel).filter(
            and_(
                ProductModel.id_categorie == category_id,
                ProductModel.actif == 'ACTIF'
            )
        ).all()
        
        return [product.to_dict() for product in products]
    
    def get_low_stock_products(self) -> List[Dict]:
        """Récupérer les produits avec un stock faible"""
        products = self.session.query(ProductModel).filter(
            and_(
                ProductModel.stock <= ProductModel.seuil_alerte,
                ProductModel.actif == 'ACTIF'
            )
        ).all()
        
        return [product.to_dict() for product in products]
    
    def _generate_sku(self, product_name: str) -> str:
        """Générer un SKU automatique basé sur le nom du produit"""
        # Prendre les 3 premières lettres du nom + timestamp
        prefix = ''.join(c for c in product_name[:3] if c.isalpha()).upper()
        timestamp = str(int(datetime.now().timestamp()))[-6:]
        return f"{prefix}-{timestamp}"
    
    def _sku_exists(self, sku: str) -> bool:
        """Vérifier si un SKU existe déjà"""
        exists = self.session.query(ProductModel).filter(
            ProductModel.sku == sku
        ).first()
        return exists is not None


class CategoryService:
    """Service métier pour la gestion des catégories"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_all_categories(self) -> List[Dict]:
        """Récupérer toutes les catégories"""
        categories = self.session.query(CategoryModel).all()
        return [category.to_dict() for category in categories]
    
    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        """Récupérer une catégorie par son ID"""
        category = self.session.query(CategoryModel).filter(
            CategoryModel.id == category_id
        ).first()
        
        return category.to_dict() if category else None
    
    def create_category(self, category_data: Dict) -> Dict:
        """Créer une nouvelle catégorie"""
        required_fields = ['nom']
        for field in required_fields:
            if field not in category_data:
                raise ValueError(f"Le champ '{field}' est requis")
        
        # Vérifier l'unicité du nom
        existing = self.session.query(CategoryModel).filter(
            CategoryModel.nom == category_data['nom']
        ).first()
        if existing:
            raise ValueError(f"Une catégorie avec le nom '{category_data['nom']}' existe déjà")
        
        category = CategoryModel(
            nom=category_data['nom'],
            description=category_data.get('description')
        )
        
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        
        return category.to_dict()
    
    def update_category(self, category_id: int, update_data: Dict) -> Optional[Dict]:
        """Mettre à jour une catégorie"""
        category = self.session.query(CategoryModel).filter(
            CategoryModel.id == category_id
        ).first()
        
        if not category:
            return None
        
        allowed_fields = ['nom', 'description']
        
        for field, value in update_data.items():
            if field in allowed_fields:
                if field == 'nom':
                    # Vérifier l'unicité du nouveau nom
                    existing = self.session.query(CategoryModel).filter(
                        and_(CategoryModel.nom == value, CategoryModel.id != category_id)
                    ).first()
                    if existing:
                        raise ValueError(f"Une catégorie avec le nom '{value}' existe déjà")
                
                setattr(category, field, value)
        
        category.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(category)
        
        return category.to_dict()


# Service de recherche avancée
class ProductSearchService:
    """Service de recherche avancée pour les produits"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def search_products(self, 
                       query: str = '',
                       category_id: Optional[int] = None,
                       min_price: Optional[float] = None,
                       max_price: Optional[float] = None,
                       in_stock_only: bool = False) -> List[Dict]:
        """Recherche avancée de produits avec filtres multiples"""
        
        db_query = self.session.query(ProductModel).filter(ProductModel.actif == 'ACTIF')
        
        # Filtrage par texte
        if query:
            text_filter = or_(
                ProductModel.nom.ilike(f'%{query}%'),
                ProductModel.description.ilike(f'%{query}%'),
                ProductModel.sku.ilike(f'%{query}%')
            )
            db_query = db_query.filter(text_filter)
        
        # Filtrage par catégorie
        if category_id:
            db_query = db_query.filter(ProductModel.id_categorie == category_id)
        
        # Filtrage par prix
        if min_price is not None:
            db_query = db_query.filter(ProductModel.prix >= min_price)
        if max_price is not None:
            db_query = db_query.filter(ProductModel.prix <= max_price)
        
        # Filtrage par disponibilité en stock
        if in_stock_only:
            db_query = db_query.filter(ProductModel.stock > 0)
        
        products = db_query.all()
        return [product.to_dict() for product in products] 