"""
Domain Services pour Product Catalog
Logique métier qui ne peut pas être placée dans un seul agrégat
"""
from typing import List, Optional
from abc import ABC, abstractmethod

from ..aggregates.product import Product
from ..value_objects.product_id import ProductId, ProductName
from src.api.bounded_contexts.shared.value_objects.entity_id import CategoryId


class IProductRepository(ABC):
    """Interface pour le repository de produits"""
    
    @abstractmethod
    def find_by_id(self, product_id: ProductId) -> Optional[Product]:
        """Trouver un produit par son ID"""
        pass
    
    @abstractmethod
    def find_by_name(self, name: ProductName) -> List[Product]:
        """Trouver des produits par nom"""
        pass
    
    @abstractmethod
    def find_by_category(self, category_id: CategoryId) -> List[Product]:
        """Trouver des produits par catégorie"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Product]:
        """Trouver tous les produits"""
        pass
    
    @abstractmethod
    def save(self, product: Product) -> None:
        """Sauvegarder un produit"""
        pass
    
    @abstractmethod
    def delete(self, product_id: ProductId) -> None:
        """Supprimer un produit"""
        pass
    
    @abstractmethod
    def exists_by_name(self, name: ProductName, exclude_id: Optional[ProductId] = None) -> bool:
        """Vérifier si un produit avec ce nom existe déjà"""
        pass


class ProductDomainService:
    """
    Domain Service pour la logique métier complexe des produits
    qui implique plusieurs agrégats ou règles métier transversales
    """
    
    def __init__(self, product_repository: IProductRepository):
        self._product_repository = product_repository
    
    def ensure_unique_product_name(self, name: ProductName, product_id: Optional[ProductId] = None) -> None:
        """
        RÈGLE MÉTIER : Assurer l'unicité du nom de produit
        """
        if self._product_repository.exists_by_name(name, product_id):
            raise ValueError(f"Un produit avec le nom '{name.value}' existe déjà")
    
    def find_products_requiring_restock(self) -> List[Product]:
        """
        RÈGLE MÉTIER : Trouver tous les produits nécessitant un réapprovisionnement
        """
        all_products = self._product_repository.find_all()
        return [
            product for product in all_products 
            if product.is_stock_below_threshold()
        ]
    
    def find_out_of_stock_products(self) -> List[Product]:
        """
        RÈGLE MÉTIER : Trouver tous les produits en rupture de stock
        """
        all_products = self._product_repository.find_all()
        return [
            product for product in all_products 
            if product.is_out_of_stock()
        ]
    
    def validate_product_for_deletion(self, product_id: ProductId) -> bool:
        """
        RÈGLE MÉTIER : Valider qu'un produit peut être supprimé
        Dans le futur, on pourrait vérifier s'il n'y a pas de commandes en cours, etc.
        """
        product = self._product_repository.find_by_id(product_id)
        if not product:
            return False
        
        return True
    
    def find_similar_products(self, product: Product) -> List[Product]:
        """
        RÈGLE MÉTIER : Trouver des produits similaires (même catégorie)
        """
        return self._product_repository.find_by_category(product.category_id)
    
    def search_products_by_name(self, search_term: str) -> List[Product]:
        """
        RÈGLE MÉTIER : Recherche de produits par nom (recherche floue)
        """
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        all_products = self._product_repository.find_all()
        search_lower = search_term.lower().strip()
        
        matches = []
        for product in all_products:
            if search_lower in product.name.value.lower():
                matches.append(product)
        
        return matches
    
    def calculate_total_inventory_value(self) -> float:
        """
        RÈGLE MÉTIER : Calculer la valeur totale de l'inventaire
        """
        all_products = self._product_repository.find_all()
        total_value = 0.0
        
        for product in all_products:
            product_value = product.price.to_float() * product.stock_quantity.value
            total_value += product_value
        
        return total_value 