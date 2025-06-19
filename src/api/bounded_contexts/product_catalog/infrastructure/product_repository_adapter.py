"""
Adaptateur de Repository pour Product Catalog
Fait le pont entre l'interface DDD et l'infrastructure existante
"""
from typing import List, Optional
from decimal import Decimal

from ..domain.services.product_domain_service import IProductRepository
from ..domain.aggregates.product import Product
from ..domain.value_objects.product_id import (
    ProductId, ProductName, ProductDescription, 
    StockQuantity, AlertThreshold
)
from src.api.bounded_contexts.shared.value_objects.money import Money
from src.api.bounded_contexts.shared.value_objects.entity_id import CategoryId
from src.persistence.repositories import RepositoryProduit
from src.persistence.database import get_db_session


class ProductRepositoryAdapter(IProductRepository):
    def __init__(self, session=None):
        self._session = session or get_db_session()
        self._repo_produit = RepositoryProduit(self._session)
    
    def find_by_id(self, product_id: ProductId) -> Optional[Product]:
        """Trouver un produit par son ID"""
        try:
            produit_entity = self._repo_produit.obtenir_par_id(product_id.value)
            if not produit_entity:
                return None
            
            return self._map_to_domain(produit_entity)
        except Exception:
            return None
    
    def find_by_name(self, name: ProductName) -> List[Product]:
        """Trouver des produits par nom"""
        try:
            produits_entities = self._repo_produit.rechercher('nom', name.value)
            return [self._map_to_domain(entity) for entity in produits_entities]
        except Exception:
            return []
    
    def find_by_category(self, category_id: CategoryId) -> List[Product]:
        """Trouver des produits par catégorie"""
        try:
            all_products = self._repo_produit.lister_tous()
            matching_products = [
                entity for entity in all_products 
                if entity.id_categorie == category_id.value
            ]
            return [self._map_to_domain(entity) for entity in matching_products]
        except Exception:
            return []
    
    def find_all(self) -> List[Product]:
        """Trouver tous les produits"""
        try:
            produits_entities = self._repo_produit.lister_tous()
            return [self._map_to_domain(entity) for entity in produits_entities]
        except Exception:
            return []
    
    def save(self, product: Product) -> None:
        """Sauvegarder un produit"""
        try:
            # Vérifier si le produit existe déjà
            existing = self._repo_produit.obtenir_par_id(product.id.value)
            
            product_data = {
                'nom': product.name.value,
                'prix': product.price.to_float(),
                'stock': product.stock_quantity.value,
                'id_categorie': product.category_id.value,
                'seuil_alerte': product.alert_threshold.value,
                'description': product.description.value if product.description else None
            }
            
            if existing:
                self._repo_produit.mettre_a_jour(product.id.value, product_data)
            else:
                self._repo_produit.creer(product_data)
            
            self._session.commit()
            
        except Exception as e:
            self._session.rollback()
            raise e
    
    def delete(self, product_id: ProductId) -> None:
        """Supprimer un produit"""
        try:
            self._repo_produit.supprimer(product_id.value)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
    
    def exists_by_name(self, name: ProductName, exclude_id: Optional[ProductId] = None) -> bool:
        """Vérifier si un produit avec ce nom existe déjà"""
        try:
            matching_products = self._repo_produit.rechercher('nom', name.value)
            
            if exclude_id:
                matching_products = [
                    p for p in matching_products 
                    if p.id != exclude_id.value
                ]
            
            return len(matching_products) > 0
        except Exception:
            return False
    
    def _map_to_domain(self, produit_entity) -> Product:
        """
        MAPPING : Convertir l'entité de persistance vers l'agrégat du domaine
        """
        try:
            # Créer les Value Objects
            product_id = ProductId(produit_entity.id)
            name = ProductName(produit_entity.nom)
            price = Money.from_float(float(produit_entity.prix))
            stock_quantity = StockQuantity(produit_entity.stock)
            category_id = CategoryId(produit_entity.id_categorie)
            alert_threshold = AlertThreshold(produit_entity.seuil_alerte)
            
            description = None
            if produit_entity.description:
                description = ProductDescription(produit_entity.description)
            
            # Créer l'agrégat avec les données existantes (sans événement de création)
            product = Product(
                _id=product_id,
                _name=name,
                _price=price,
                _stock_quantity=stock_quantity,
                _category_id=category_id,
                _alert_threshold=alert_threshold,
                _description=description,
                _events=[]  # Pas d'événements pour les objets chargés depuis la DB
            )
            
            return product
            
        except Exception as e:
            raise ValueError(f"Erreur lors du mapping vers le domaine: {str(e)}")
    
    def close(self):
        """Fermer la session"""
        if self._session:
            self._session.close() 