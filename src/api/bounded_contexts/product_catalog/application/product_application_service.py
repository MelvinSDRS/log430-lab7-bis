"""
Application Service pour Product Catalog
Orchestre les opérations du domaine et coordonne avec l'infrastructure
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ..domain.aggregates.product import Product
from ..domain.services.product_domain_service import ProductDomainService, IProductRepository
from ..domain.value_objects.product_id import (
    ProductId, ProductName, ProductDescription, 
    StockQuantity, AlertThreshold
)
from src.api.bounded_contexts.shared.value_objects.money import Money
from src.api.bounded_contexts.shared.value_objects.entity_id import CategoryId
from src.api.bounded_contexts.shared.events.domain_event import DomainEventPublisher
import logging

logger = logging.getLogger(__name__)


class ProductApplicationService:
    """
    APPLICATION SERVICE : Orchestration des cas d'usage pour Product Catalog
    Point d'entrée pour l'API REST (remplace les anciens services métier)
    """
    
    def __init__(self, product_repository: IProductRepository):
        self._product_repository = product_repository
        self._domain_service = ProductDomainService(product_repository)
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        UC4 - Récupérer un produit par son ID
        """
        try:
            domain_product_id = ProductId(product_id)
            product = self._product_repository.find_by_id(domain_product_id)
            
            if not product:
                return None
            
            logger.info(f"Produit récupéré - ID: {product_id}")
            return product.to_dict()
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du produit {product_id}: {str(e)}")
            raise
    
    def list_products(self, 
                     search: Optional[str] = None, 
                     category_id: Optional[int] = None,
                     sort_field: str = 'nom',
                     sort_order: str = 'asc') -> List[Dict[str, Any]]:
        """
        UC4 - Lister les produits avec filtrage et tri
        """
        try:
            if search:
                products = self._domain_service.search_products_by_name(search)
            elif category_id:
                domain_category_id = CategoryId(category_id)
                products = self._product_repository.find_by_category(domain_category_id)
            else:
                products = self._product_repository.find_all()
            
            if sort_field == 'nom':
                products.sort(key=lambda p: p.name.value, reverse=(sort_order == 'desc'))
            elif sort_field == 'prix':
                products.sort(key=lambda p: p.price.amount, reverse=(sort_order == 'desc'))
            
            result = [product.to_dict() for product in products]
            logger.info(f"Liste produits récupérée - Total: {len(result)}, Recherche: {search}, Catégorie: {category_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des produits: {str(e)}")
            raise
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        UC4 - Créer un nouveau produit
        """
        try:
            name = ProductName(product_data['nom'])
            price = Money.from_float(float(product_data['prix']))
            stock_quantity = StockQuantity(product_data['stock'])
            category_id = CategoryId(product_data['id_categorie'])
            alert_threshold = AlertThreshold(product_data.get('seuil_alerte', 5))
            
            description = None
            if product_data.get('description'):
                description = ProductDescription(product_data['description'])
            
            self._domain_service.ensure_unique_product_name(name)
            
            temp_id = ProductId(0)
            product = Product.create(
                product_id=temp_id,
                name=name,
                price=price,
                stock_quantity=stock_quantity,
                category_id=category_id,
                alert_threshold=alert_threshold,
                description=description
            )
            
            self._product_repository.save(product)
            
            events = product.get_uncommitted_events()
            DomainEventPublisher.publish(events)
            
            created_products = self._domain_service.search_products_by_name(name.value)
            if created_products:
                created_product = created_products[0]
                logger.info(f"Produit créé - ID: {created_product.id.value}, Nom: {created_product.name.value}")
                return created_product.to_dict()
            
            raise Exception("Impossible de récupérer le produit créé")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du produit: {str(e)}")
            raise
    
    def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        UC4 - Mettre à jour un produit existant
        """
        try:
            domain_product_id = ProductId(product_id)
            product = self._product_repository.find_by_id(domain_product_id)
            
            if not product:
                raise ValueError(f"Produit avec l'ID {product_id} introuvable")
            
            if 'nom' in product_data:
                new_name = ProductName(product_data['nom'])
                self._domain_service.ensure_unique_product_name(new_name, domain_product_id)
                product.update_name(new_name)
            
            if 'prix' in product_data:
                new_price = Money.from_float(float(product_data['prix']))
                product.update_price(new_price)
            
            if 'stock' in product_data:
                new_stock = StockQuantity(product_data['stock'])
                product.update_stock_quantity(new_stock)
            
            if 'id_categorie' in product_data:
                new_category = CategoryId(product_data['id_categorie'])
                product.update_category(new_category)
            
            if 'seuil_alerte' in product_data:
                new_threshold = AlertThreshold(product_data['seuil_alerte'])
                product.update_alert_threshold(new_threshold)
            
            if 'description' in product_data:
                new_description = None
                if product_data['description']:
                    new_description = ProductDescription(product_data['description'])
                product.update_description(new_description)
            
            self._product_repository.save(product)
            
            events = product.get_uncommitted_events()
            DomainEventPublisher.publish(events)
            
            logger.info(f"Produit mis à jour - ID: {product_id}")
            return product.to_dict()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du produit {product_id}: {str(e)}")
            raise
    
    def delete_product(self, product_id: int) -> bool:
        """
        UC4 - Supprimer un produit
        """
        try:
            domain_product_id = ProductId(product_id)
            
            if not self._domain_service.validate_product_for_deletion(domain_product_id):
                raise ValueError(f"Le produit {product_id} ne peut pas être supprimé")
            
            product = self._product_repository.find_by_id(domain_product_id)
            if not product:
                return False
            
            product.mark_for_deletion()
            
            self._product_repository.delete(domain_product_id)
            
            events = product.get_uncommitted_events()
            DomainEventPublisher.publish(events)
            
            logger.info(f"Produit supprimé - ID: {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du produit {product_id}: {str(e)}")
            raise
    
    def get_products_requiring_restock(self) -> List[Dict[str, Any]]:
        """
        Méthode utilitaire : Produits nécessitant un réapprovisionnement
        """
        try:
            products = self._domain_service.find_products_requiring_restock()
            return [product.to_dict() for product in products]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des produits en rupture: {str(e)}")
            raise
    
    def get_inventory_total_value(self) -> float:
        """
        Méthode utilitaire : Valeur totale de l'inventaire
        """
        try:
            return self._domain_service.calculate_total_inventory_value()
        except Exception as e:
            logger.error(f"Erreur lors du calcul de la valeur de l'inventaire: {str(e)}")
            raise 